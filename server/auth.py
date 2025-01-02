from functools import wraps
from flask import request, jsonify, session, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
import logging

# إعداد التسجيل
logger = logging.getLogger('silvarium_auth')
login_manager = LoginManager()

class User:
    def __init__(self, id, username, role, is_approved, status):
        self.id = id
        self.username = username
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
            return user_data
        except Exception as e:
            logger.error(f"خطأ في البحث عن المستخدم: {str(e)}")
            return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({"error": "غير مصرح بالوصول"}), 403
        return f(*args, **kwargs)
    return decorated_function

def setup_auth(app):
    """إعداد المصادقة"""
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username, role, is_approved, status 
                FROM users 
                WHERE id = %s
            """, (user_id,))
            user_data = cur.fetchone()
            if user_data:
                return User(*user_data)
            return None
        except Exception as e:
            logger.error(f"خطأ في تحميل المستخدم: {str(e)}")
            return None
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    @app.route('/api/login', methods=['POST'])
    def login():
        """تسجيل الدخول"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "البيانات غير صالحة"}), 400

            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({"error": "يجب توفير اسم المستخدم وكلمة المرور"}), 400

            logger.info(f"محاولة تسجيل الدخول للمستخدم: {username}")
            user_data = User.get_by_username(username)

            if not user_data:
                logger.warning(f"محاولة تسجيل دخول فاشلة - المستخدم غير موجود: {username}")
                return jsonify({"error": "اسم المستخدم غير صحيح"}), 401

            if not check_password_hash(user_data[2], password):
                logger.warning(f"محاولة تسجيل دخول فاشلة - كلمة مرور غير صحيحة: {username}")
                return jsonify({"error": "كلمة المرور غير صحيحة"}), 401

            if not user_data[4]:  # is_approved
                logger.warning(f"محاولة تسجيل دخول فاشلة - الحساب غير معتمد: {username}")
                return jsonify({"error": "الحساب في انتظار الموافقة"}), 401

            if user_data[5] == 'blocked':  # status
                logger.warning(f"محاولة تسجيل دخول فاشلة - الحساب محظور: {username}")
                return jsonify({"error": "تم حظر الحساب"}), 401

            user = User(user_data[0], user_data[1], user_data[3], user_data[4], user_data[5])
            login_user(user)
            logger.info(f"تم تسجيل دخول المستخدم بنجاح: {username}")

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

    @app.route('/api/logout', methods=['POST'])
    @login_required
    def logout():
        """تسجيل الخروج"""
        try:
            username = current_user.username
            logout_user()
            logger.info(f"تم تسجيل خروج المستخدم بنجاح: {username}")
            return jsonify({"message": "تم تسجيل الخروج بنجاح"})
        except Exception as e:
            logger.error(f"خطأ في تسجيل الخروج: {str(e)}")
            return jsonify({"error": "حدث خطأ في تسجيل الخروج"}), 500

    @app.route('/api/user', methods=['GET'])
    def get_current_user():
        """الحصول على معلومات المستخدم الحالي"""
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

    return app