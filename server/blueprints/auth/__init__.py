"""Authentication blueprint for the application"""
from flask import Blueprint, request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import os
import psycopg2
from datetime import datetime
import traceback
from .firebase_service import firebase_auth

# إعداد التسجيل
logger = logging.getLogger('silvarium_auth')
logger.setLevel(logging.INFO)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
login_manager = LoginManager()

def get_bilingual_message(ar_msg: str, en_msg: str) -> dict:
    """Return bilingual message format"""
    return {
        "message": {
            "ar": ar_msg,
            "en": en_msg
        }
    }

class User:
    def __init__(self, id, username, password=None, role='user', is_approved=True, status='active'):
        self.id = id
        self.username = username
        self.password = password
        self.role = role
        self.is_approved = is_approved
        self.status = status
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get_by_username(username):
        """البحث عن مستخدم باستخدام اسم المستخدم"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                SELECT id, username, password, role, is_approved, status 
                FROM users 
                WHERE username = %s
            """, (username,))

            user_data = cur.fetchone()
            cur.close()
            conn.close()

            if user_data:
                return User(
                    id=user_data[0],
                    username=user_data[1],
                    password=user_data[2],
                    role=user_data[3],
                    is_approved=user_data[4],
                    status=user_data[5]
                )
            return None

        except Exception as e:
            logger.error(f"خطأ في البحث عن المستخدم: {str(e)}")
            return None

def init_auth(app):
    """تهيئة المصادقة"""
    global login_manager

    # Check if login manager is already initialized
    if not hasattr(app, 'login_manager'):
        login_manager.init_app(app)
        app.login_manager = login_manager

        logger.info("تم تهيئة مدير تسجيل الدخول")

    # Set login view
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                SELECT id, username, password, role, is_approved, status 
                FROM users 
                WHERE id = %s
            """, (user_id,))

            user_data = cur.fetchone()
            cur.close()
            conn.close()

            if user_data:
                return User(
                    id=user_data[0],
                    username=user_data[1],
                    password=user_data[2],
                    role=user_data[3],
                    is_approved=user_data[4],
                    status=user_data[5]
                )
            return None

        except Exception as e:
            logger.error(f"خطأ في تحميل المستخدم: {str(e)}")
            return None

    # التأكد من وجود جدول المستخدمين
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'user',
                is_approved BOOLEAN DEFAULT true,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                phone_number VARCHAR(20) UNIQUE
            )
        """)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("تم التأكد من وجود جدول المستخدمين")
    except Exception as e:
        logger.error(f"خطأ في إنشاء جدول المستخدمين: {str(e)}")

    # Only register the blueprint if it hasn't been registered yet
    if 'auth' not in app.blueprints:
        app.register_blueprint(auth_bp)
        logger.info("تم تسجيل مخطط المصادقة")

    return app

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "يجب توفير اسم المستخدم وكلمة المرور"}), 400

        user = User.get_by_username(username)
        if not user or not check_password_hash(user.password, password):
            return jsonify({"error": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401

        if not user.is_approved:
            return jsonify({"error": "الحساب في انتظار الموافقة"}), 401

        if user.status != 'active':
            return jsonify({"error": "الحساب غير نشط"}), 401

        login_user(user)
        return jsonify({
            "message": "تم تسجيل الدخول بنجاح",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            }
        })

    except Exception as e:
        logger.error(f"خطأ في تسجيل الدخول: {str(e)}")
        return jsonify({"error": "حدث خطأ في تسجيل الدخول"}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "يجب توفير اسم المستخدم وكلمة المرور"}), 400

        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # التحقق من وجود المستخدم
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "اسم المستخدم موجود بالفعل"}), 400

        # إنشاء مستخدم جديد
        hashed_password = generate_password_hash(password)
        cur.execute("""
            INSERT INTO users (username, password, created_at)
            VALUES (%s, %s, %s)
            RETURNING id, username, role, is_approved, status
        """, (username, hashed_password, datetime.now()))

        user_data = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if user_data:
            user = User(
                id=user_data[0],
                username=user_data[1],
                role=user_data[2],
                is_approved=user_data[3],
                status=user_data[4]
            )
            login_user(user)
            return jsonify({
                "message": "تم التسجيل بنجاح",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role
                }
            })

        return jsonify({"error": "فشل في إنشاء المستخدم"}), 500

    except Exception as e:
        logger.error(f"خطأ في التسجيل: {str(e)}")
        return jsonify({"error": "حدث خطأ في التسجيل"}), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    try:
        logout_user()
        return jsonify({"message": "تم تسجيل الخروج بنجاح"})
    except Exception as e:
        logger.error(f"خطأ في تسجيل الخروج: {str(e)}")
        return jsonify({"error": "حدث خطأ في تسجيل الخروج"}), 500

@auth_bp.route('/user', methods=['GET'])
def get_current_user():
    try:
        if current_user.is_authenticated:
            return jsonify({
                "id": current_user.id,
                "username": current_user.username,
                "role": current_user.role,
                "isApproved": current_user.is_approved,
                "status": current_user.status
            })
        return jsonify({"error": "لم يتم تسجيل الدخول"}), 401
    except Exception as e:
        logger.error(f"خطأ في جلب معلومات المستخدم: {str(e)}")
        return jsonify({"error": "حدث خطأ في جلب معلومات المستخدم"}), 500

@auth_bp.route('/verify-phone', methods=['POST'])
def verify_phone():
    """التحقق من رقم الهاتف"""
    try:
        data = request.get_json()
        phone_number = data.get('phoneNumber')
        code = data.get('code')
        verification_id = data.get('verificationId')

        if not all([phone_number, code, verification_id]):
            logger.warning("بيانات غير مكتملة في طلب التحقق من رقم الهاتف")
            return jsonify(get_bilingual_message(
                "يجب توفير رقم الهاتف ورمز التحقق",
                "Phone number and verification code are required"
            )), 400

        # التحقق من رقم الهاتف باستخدام Firebase
        result = firebase_auth.verify_phone_number(phone_number, verification_id)
        if not result:
            logger.warning(f"فشل في التحقق من رقم الهاتف: {phone_number}")
            return jsonify(get_bilingual_message(
                "فشل في التحقق من رقم الهاتف",
                "Failed to verify phone number"
            )), 400

        logger.info(f"تم التحقق من رقم الهاتف بنجاح: {phone_number}")
        return jsonify(get_bilingual_message(
            "تم التحقق من رقم الهاتف بنجاح",
            "Phone number verified successfully"
        ))

    except Exception as e:
        logger.error(f"خطأ في التحقق من رقم الهاتف: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify(get_bilingual_message(
            "حدث خطأ في التحقق من رقم الهاتف",
            "Error verifying phone number"
        )), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """إعادة تعيين كلمة المرور | Reset Password"""
    try:
        data = request.get_json()
        username = data.get('username')
        new_password = data.get('password')
        verification_id = data.get('verificationId')

        if not all([username, new_password, verification_id]):
            logger.warning("بيانات غير مكتملة في طلب إعادة تعيين كلمة المرور")
            return jsonify(get_bilingual_message(
                "يجب توفير جميع البيانات المطلوبة",
                "All required data must be provided"
            )), 400

        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # التحقق من وجود المستخدم | Check if user exists
        cur.execute("""
            SELECT id, username, status, is_approved 
            FROM users 
            WHERE username = %s
        """, (username,))
        user = cur.fetchone()

        if not user:
            logger.warning(f"محاولة إعادة تعيين كلمة المرور لمستخدم غير موجود: {username}")
            cur.close()
            conn.close()
            return jsonify(get_bilingual_message(
                "المستخدم غير موجود",
                "User not found"
            )), 404

        # التحقق من حالة المستخدم | Check user status
        user_id, user_username, user_status, is_approved = user

        if not is_approved:
            logger.warning(f"محاولة إعادة تعيين كلمة المرور لحساب غير معتمد: {username}")
            return jsonify(get_bilingual_message(
                "الحساب غير معتمد، يرجى الاتصال بالمسؤول",
                "Account not approved, please contact administrator"
            )), 403

        if user_status != 'active':
            logger.warning(f"محاولة إعادة تعيين كلمة المرور لحساب غير نشط: {username}")
            return jsonify(get_bilingual_message(
                "الحساب غير نشط، يرجى الاتصال بالمسؤول",
                "Account not active, please contact administrator"
            )), 403

        # تحديث كلمة المرور | Update password
        hashed_password = generate_password_hash(new_password)
        cur.execute(
            "UPDATE users SET password = %s WHERE username = %s",
            (hashed_password, username)
        )

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"تم إعادة تعيين كلمة المرور بنجاح للمستخدم: {username}")
        return jsonify(get_bilingual_message(
            "تم إعادة تعيين كلمة المرور بنجاح",
            "Password reset successfully"
        ))

    except Exception as e:
        logger.error(f"خطأ في إعادة تعيين كلمة المرور: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify(get_bilingual_message(
            "حدث خطأ في إعادة تعيين كلمة المرور",
            "Error resetting password"
        )), 500