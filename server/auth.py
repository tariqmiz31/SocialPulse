import logging
from functools import wraps
from flask import request, jsonify, session, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
import traceback

# إعداد التسجيل
logger = logging.getLogger('silvarium_auth')
logger.setLevel(logging.DEBUG)

# إضافة معالج لتسجيل السجلات في ملف
handler = logging.FileHandler('/tmp/auth.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

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
            logger.debug(f"جاري البحث عن المستخدم: {username}")
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                SELECT id, username, password, role, is_approved, status 
                FROM users 
                WHERE username = %s
            """, (username,))

            user_data = cur.fetchone()

            if user_data:
                logger.debug(f"تم العثور على المستخدم: {username}")
                logger.debug(f"حالة المستخدم - معتمد: {user_data[4]}, الحالة: {user_data[5]}")
                return user_data

            logger.warning(f"لم يتم العثور على المستخدم: {username}")
            return None

        except Exception as e:
            logger.error(f"خطأ في البحث عن المستخدم: {str(e)}")
            logger.error(traceback.format_exc())
            return None
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            logger.warning(f"محاولة وصول غير مصرح بها من المستخدم: {current_user.username if current_user.is_authenticated else 'غير مسجل'}")
            return jsonify({"error": "غير مصرح بالوصول"}), 403
        return f(*args, **kwargs)
    return decorated_function

def setup_auth(app):
    """إعداد المصادقة"""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.session_protection = 'strong'

    @login_manager.user_loader
    def load_user(user_id):
        """تحميل المستخدم من قاعدة البيانات"""
        try:
            logger.debug(f"محاولة تحميل المستخدم بالمعرف: {user_id}")
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                SELECT id, username, role, is_approved, status 
                FROM users 
                WHERE id = %s
            """, (user_id,))

            user_data = cur.fetchone()

            if user_data:
                logger.debug(f"تم تحميل المستخدم بنجاح: {user_data[1]}")
                return User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4])

            logger.warning(f"فشل تحميل المستخدم بالمعرف: {user_id}")
            return None

        except Exception as e:
            logger.error(f"خطأ في تحميل المستخدم: {str(e)}")
            logger.error(traceback.format_exc())
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
            logger.debug(f"بيانات طلب تسجيل الدخول: {data}")

            if not data:
                logger.warning("محاولة تسجيل دخول بدون بيانات")
                return jsonify({"error": "البيانات غير صالحة"}), 400

            username = data.get('username')
            password = data.get('password')

            logger.debug(f"محاولة تسجيل الدخول - المستخدم: {username}")

            if not username or not password:
                logger.warning(f"بيانات غير مكتملة - اسم المستخدم: {username}")
                return jsonify({"error": "يجب توفير اسم المستخدم وكلمة المرور"}), 400

            user_data = User.get_by_username(username)

            if not user_data:
                logger.warning(f"المستخدم غير موجود: {username}")
                return jsonify({"error": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401

            stored_password = user_data[2]
            logger.debug(f"التحقق من كلمة المرور للمستخدم: {username}")

            if not check_password_hash(stored_password, password):
                logger.warning(f"كلمة مرور غير صحيحة للمستخدم: {username}")
                return jsonify({"error": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401

            if not user_data[4]:  # is_approved
                logger.warning(f"حساب غير معتمد: {username}")
                return jsonify({"error": "الحساب في انتظار الموافقة"}), 401

            if user_data[5] == 'blocked':  # status
                logger.warning(f"حساب محظور: {username}")
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
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

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
                logger.debug(f"تم جلب معلومات المستخدم: {current_user.username}")
                return jsonify({
                    "id": current_user.id,
                    "username": current_user.username,
                    "role": current_user.role,
                    "isApproved": current_user.is_approved,
                    "status": current_user.status
                })
            logger.debug("محاولة جلب معلومات المستخدم - غير مسجل الدخول")
            return jsonify({"error": "لم يتم تسجيل الدخول"}), 401
        except Exception as e:
            logger.error(f"خطأ في جلب معلومات المستخدم: {str(e)}")
            return jsonify({"error": "حدث خطأ في جلب معلومات المستخدم"}), 500

    return app