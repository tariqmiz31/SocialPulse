"""Authentication blueprint for the application"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import os
import psycopg2
from datetime import datetime, timedelta
import random
import string
import time
import traceback

# Import SMS service at the top of the file
try:
    from .sms_service import sms_service
    logger = logging.getLogger('silvarium_auth')
    logger.setLevel(logging.INFO)
except Exception as e:
    logger.error(f"Error importing SMS service: {str(e)}")
    sms_service = None

# Create blueprint with unique name
auth_bp = Blueprint('silvarium_auth', __name__, url_prefix='/api/auth')

def generate_verification_code():
    """Generate a 4-digit verification code | توليد رمز تحقق من 4 أرقام"""
    return ''.join(random.choices(string.digits, k=4))

def get_bilingual_message(ar_msg: str, en_msg: str) -> dict:
    """Return bilingual message format"""
    return {
        "message": {
            "ar": ar_msg,
            "en": en_msg
        }
    }

@auth_bp.route('/send-verification-code', methods=['POST'])
async def send_verification_code():
    """إرسال رمز التحقق عبر SMS | Send verification code via SMS"""
    try:
        data = request.get_json()
        phone_number = data.get('phoneNumber')
        action = data.get('action', 'verify')  # 'verify' or 'reset'

        logger.info(f"Received verification code request for phone number: {phone_number}, action: {action}")

        if not phone_number:
            logger.warning("لم يتم توفير رقم الهاتف | Phone number not provided")
            return jsonify(get_bilingual_message(
                "يجب توفير رقم الهاتف",
                "Phone number is required"
            )), 400

        # Check rate limit
        if not await sms_service.check_rate_limit(phone_number):
            logger.warning(f"تم تجاوز الحد المسموح لإرسال الرموز: {phone_number}")
            return jsonify(get_bilingual_message(
                "تم تجاوز الحد المسموح من المحاولات، يرجى المحاولة لاحقاً",
                "Rate limit exceeded, please try again later"
            )), 429

        # Generate verification code
        verification_code = generate_verification_code()
        expires_at = datetime.now() + timedelta(minutes=10)

        # Save code in database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # Check if phone number exists
        cur.execute("""
            SELECT id, status FROM users 
            WHERE phone_number = %s
        """, (phone_number,))

        user = cur.fetchone()

        if user:
            # Update existing user's verification code
            user_id, user_status = user
            if action == 'verify' and user_status == 'active':
                return jsonify(get_bilingual_message(
                    "رقم الهاتف مسجل مسبقاً",
                    "Phone number is already verified"
                )), 400

            cur.execute("""
                UPDATE users 
                SET verification_code = %s, 
                    verification_code_expires_at = %s 
                WHERE id = %s
            """, (verification_code, expires_at, user_id))
        else:
            # Create temporary user record
            temp_username = f"temp_{phone_number}_{int(time.time())}"
            temp_password = generate_password_hash('temp_password')

            cur.execute("""
                INSERT INTO users (username, password, phone_number, verification_code, verification_code_expires_at, role, status)
                VALUES (%s, %s, %s, %s, %s, 'user', 'pending')
            """, (temp_username, temp_password, phone_number, verification_code, expires_at))

        conn.commit()
        cur.close()
        conn.close()

        # Send verification code
        success, error = await sms_service.send_verification_code(phone_number, verification_code)
        if not success:
            return jsonify(get_bilingual_message(
                "فشل في إرسال رمز التحقق",
                f"Failed to send verification code: {error}"
            )), 500

        return jsonify(get_bilingual_message(
            "تم إرسال رمز التحقق بنجاح",
            "Verification code sent successfully"
        ))

    except Exception as e:
        logger.error(f"خطأ في إرسال رمز التحقق: {str(e)}")
        logger.error(traceback.format_exc())
        if 'conn' in locals():
            conn.close()
        return jsonify(get_bilingual_message(
            "حدث خطأ في إرسال رمز التحقق",
            "Error sending verification code"
        )), 500

@auth_bp.route('/verify-phone', methods=['POST'])
async def verify_phone():
    """التحقق من رقم الهاتف | Verify phone number"""
    try:
        data = request.get_json()
        phone_number = data.get('phoneNumber')
        code = data.get('code')
        action = data.get('action', 'verify')  # 'verify' or 'reset'

        if not all([phone_number, code]):
            logger.warning("بيانات غير مكتملة في طلب التحقق من رقم الهاتف")
            return jsonify(get_bilingual_message(
                "يجب توفير رقم الهاتف ورمز التحقق",
                "Phone number and verification code are required"
            )), 400

        # Verify code
        success, error = await sms_service.verify_code(phone_number, code)
        if not success:
            return jsonify(get_bilingual_message(
                error,
                "Verification failed"
            )), 400

        # Clear verification code after successful verification
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # Update user status based on action
        if action == 'verify':
            cur.execute("""
                UPDATE users 
                SET verification_code = NULL, 
                    verification_code_expires_at = NULL,
                    status = 'active'
                WHERE phone_number = %s
                RETURNING id
            """, (phone_number,))
        else:
            cur.execute("""
                UPDATE users 
                SET verification_code = NULL, 
                    verification_code_expires_at = NULL
                WHERE phone_number = %s
                RETURNING id
            """, (phone_number,))

        user_id = cur.fetchone()
        if not user_id:
            cur.close()
            conn.close()
            return jsonify(get_bilingual_message(
                "لم يتم العثور على المستخدم",
                "User not found"
            )), 404

        conn.commit()
        cur.close()
        conn.close()

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

class User:
    def __init__(self, id, username, password=None, role='user', is_approved=True, status='active', verification_code=None, verification_code_expires_at=None):
        self.id = id
        self.username = username
        self.password = password
        self.role = role
        self.is_approved = is_approved
        self.status = status
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
        self.verification_code = verification_code
        self.verification_code_expires_at = verification_code_expires_at

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get_by_username(username):
        """البحث عن مستخدم باستخدام اسم المستخدم"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                SELECT id, username, password, role, is_approved, status, verification_code, verification_code_expires_at
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
                    status=user_data[5],
                    verification_code=user_data[6],
                    verification_code_expires_at=user_data[7]
                )
            return None

        except Exception as e:
            logger.error(f"خطأ في البحث عن المستخدم: {str(e)}")
            return None

def init_verification_tables() -> bool:
    """Initialize verification related tables | تهيئة جداول التحقق"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # Create verification_attempts table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS verification_attempts (
                id SERIAL PRIMARY KEY,
                phone_number VARCHAR(20) NOT NULL,
                attempt_time TIMESTAMP NOT NULL
            )
        """)

        # Add verification columns to users table if they don't exist
        cur.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20) UNIQUE,
            ADD COLUMN IF NOT EXISTS verification_code VARCHAR(4),
            ADD COLUMN IF NOT EXISTS verification_code_expires_at TIMESTAMP
        """)

        conn.commit()
        cur.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"خطأ في تهيئة جداول التحقق: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def init_auth(app):
    """تهيئة المصادقة | Initialize authentication"""
    try:
        # Initialize login manager if not already initialized
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'silvarium_auth.login'
        logger.info("تم تهيئة مدير تسجيل الدخول")

        @login_manager.user_loader
        def load_user(user_id):
            try:
                conn = psycopg2.connect(os.getenv('DATABASE_URL'))
                cur = conn.cursor()

                cur.execute("""
                    SELECT id, username, password, role, is_approved, status, verification_code, verification_code_expires_at
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
                        status=user_data[5],
                        verification_code=user_data[6],
                        verification_code_expires_at=user_data[7]
                    )
                return None

            except Exception as e:
                logger.error(f"خطأ في تحميل المستخدم: {str(e)}")
                return None

        # Create users table if not exists
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # Initialize verification tables before creating the users table.
        if not init_verification_tables():
            raise Exception("Failed to initialize verification tables.")


        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'user',
                is_approved BOOLEAN DEFAULT true,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                phone_number VARCHAR(20) UNIQUE,
                verification_code VARCHAR(4),
                verification_code_expires_at TIMESTAMP
            )
        """)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("تم التأكد من وجود جدول المستخدمين")

        # Register blueprint only if not already registered
        if 'silvarium_auth' not in app.blueprints:
            app.register_blueprint(auth_bp)
            logger.info("تم تسجيل مخطط المصادقة")

        return app

    except Exception as e:
        logger.error(f"خطأ في تهيئة المصادقة: {str(e)}")
        return None

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

        # التحقق من الرمز باستخدام Firebase
        try:
            # This section likely needs to be updated to use the local verification method instead of Firebase
            # Placeholder for local verification logic
            if True: # Replace with actual verification logic using verification_id
                pass
            else:
                logger.error("Verification failed.")
                return jsonify(get_bilingual_message("فشل في التحقق", "Verification failed")), 401

        except Exception as e:
            logger.error(f"خطأ في التحقق من رمز الجلسة: {str(e)}")
            return jsonify(get_bilingual_message(
                "فشل في التحقق من جلسة التحقق",
                "Failed to verify session"
            )), 401

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

@auth_bp.route('/link-phone', methods=['POST'])
def link_phone():
    """ربط رقم الهاتف بالمستخدم | Link phone number to user"""
    try:
        data = request.get_json()
        username = data.get('username')
        phone_number = data.get('phoneNumber')

        if not all([username, phone_number]):
            logger.warning("بيانات غير مكتملة في طلب ربط رقم الهاتف")
            return jsonify(get_bilingual_message(
                "يجب توفير اسم المستخدم ورقم الهاتف",
                "Username and phone number are required"
            )), 400

        # التحقق من وجود المستخدم | Check if user exists
        user = User.get_by_username(username)
        if not user:
            logger.warning(f"محاولة ربط رقم الهاتف لمستخدم غير موجود: {username}")
            return jsonify(get_bilingual_message(
                "المستخدم غير موجود",
                "User not found"
            )), 404

        # ربط رقم الهاتف باستخدام Firebase | Link phone number using Firebase
        # This section needs to be removed or replaced with local database update
        # Placeholder for local database update

        # تحديث رقم الهاتف في قاعدة البيانات | Update phone number in database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        cur.execute(
            "UPDATE users SET phone_number = %s WHERE username = %s",
            (phone_number, username)
        )

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"تم ربط رقم الهاتف بنجاح للمستخدم: {username}")
        return jsonify(get_bilingual_message(
            "تم ربط رقم الهاتف بنجاح",
            "Phone number linked successfully"
        ))

    except Exception as e:
        logger.error(f"خطأ في ربط رقم الهاتف: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify(get_bilingual_message(
            "حدث خطأ في ربط رقم الهاتف",
            "Error linking phone number"
        )), 500

#Import firebase service after blueprint creation to avoid circular imports
try:
    from .firebase_service import firebase_auth
    logger.info("Firebase service imported successfully")
except Exception as e:
    logger.error(f"Error importing Firebase service: {str(e)}")
    firebase_auth = None