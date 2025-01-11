from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from server.database import get_db
from server import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/login', methods=['POST'])
def login():
    """تسجيل الدخول"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'message': 'اسم المستخدم وكلمة المرور مطلوبة'}), 400

        db = get_db()
        cursor = db.cursor()
        
        try:
            cursor.execute("""
                SELECT id, username, email, role, status, password
                FROM users
                WHERE username = %s AND status = 'active'
            """, (username,))
            
            user_data = cursor.fetchone()
            
            if user_data and check_password_hash(user_data[5], password):
                user = User(user_data)
                login_user(user)
                return jsonify({
                    'message': 'تم تسجيل الدخول بنجاح',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'role': user.role
                    }
                })
            
            return jsonify({'message': 'اسم المستخدم أو كلمة المرور غير صحيحة'}), 401
            
        finally:
            cursor.close()
            
    except Exception as e:
        return jsonify({'message': f'حدث خطأ أثناء تسجيل الدخول: {str(e)}'}), 500

@auth_bp.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """تسجيل الخروج"""
    logout_user()
    return jsonify({'message': 'تم تسجيل الخروج بنجاح'})
