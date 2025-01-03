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

class User:
    def __init__(self, id, username, role='user', is_approved=False, status='pending'):
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

            if user_data:
                return User(
                    id=user_data[0],
                    username=user_data[1],
                    role=user_data[3],
                    is_approved=user_data[4],
                    status=user_data[5]
                ), user_data[2]  # Return user object and hashed password

            return None, None

        except Exception as e:
            logger.error(f"خطأ في البحث عن المستخدم: {str(e)}")
            logger.error(traceback.format_exc())
            return None, None

def setup_auth(app):
    """إعداد المصادقة"""
    login_manager = LoginManager()
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
            cur.close()
            conn.close()

            if user_data:
                return User(
                    id=user_data[0],
                    username=user_data[1],
                    role=user_data[2],
                    is_approved=user_data[3],
                    status=user_data[4]
                )

            return None

        except Exception as e:
            logger.error(f"خطأ في تحميل المستخدم: {str(e)}")
            return None

    @app.route('/api/login', methods=['POST'])
    def login():
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({"error": "يجب توفير اسم المستخدم وكلمة المرور"}), 400

            user, hashed_password = User.get_by_username(username)
            if not user or not hashed_password:
                return jsonify({"error": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401

            if not check_password_hash(hashed_password, password):
                return jsonify({"error": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401

            if not user.is_approved:
                return jsonify({"error": "الحساب في انتظار الموافقة"}), 401

            if user.status == 'blocked':
                return jsonify({"error": "تم حظر الحساب"}), 401

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

    @app.route('/api/logout', methods=['POST'])
    @login_required
    def logout():
        try:
            logout_user()
            return jsonify({"message": "تم تسجيل الخروج بنجاح"})
        except Exception as e:
            logger.error(f"خطأ في تسجيل الخروج: {str(e)}")
            return jsonify({"error": "حدث خطأ في تسجيل الخروج"}), 500

    @app.route('/api/user', methods=['GET'])
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

    return app