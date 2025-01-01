from functools import wraps
from flask import request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({"error": "غير مصرح بالوصول"}), 403
        return f(*args, **kwargs)
    return decorated_function

def setup_auth(app):
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        try:
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
        finally:
            cur.close()
            conn.close()

    @app.route('/api/login', methods=['POST'])
    def login():
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "يجب توفير اسم المستخدم وكلمة المرور"}), 400

        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username, password, role, is_approved, status 
                FROM users 
                WHERE username = %s
            """, (username,))
            user_data = cur.fetchone()

            if not user_data:
                return jsonify({"error": "اسم المستخدم غير صحيح"}), 401

            if not check_password_hash(user_data[2], password):
                return jsonify({"error": "كلمة المرور غير صحيحة"}), 401

            if not user_data[4]:  # is_approved
                return jsonify({"error": "الحساب في انتظار الموافقة"}), 401

            if user_data[5] == 'blocked':  # status
                return jsonify({"error": "تم حظر الحساب"}), 401

            user = User(user_data[0], user_data[1], user_data[3], user_data[4], user_data[5])
            login_user(user)

            return jsonify({
                "message": "تم تسجيل الدخول بنجاح",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role
                }
            })
        finally:
            cur.close()
            conn.close()

    @app.route('/api/logout', methods=['POST'])
    @login_required
    def logout():
        logout_user()
        return jsonify({"message": "تم تسجيل الخروج بنجاح"})

    @app.route('/api/user', methods=['GET'])
    def get_current_user():
        if current_user.is_authenticated:
            return jsonify({
                "id": current_user.id,
                "username": current_user.username,
                "role": current_user.role,
                "isApproved": current_user.is_approved,
                "status": current_user.status
            })
        return jsonify({"error": "لم يتم تسجيل الدخول"}), 401

    return app
