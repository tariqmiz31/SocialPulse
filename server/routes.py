from flask import Flask, send_from_directory, jsonify, request, current_app
import os
from werkzeug.security import generate_password_hash
from server.auth import login_required, admin_required, setup_auth
import psycopg2
from datetime import datetime
import logging

def setup_routes(app: Flask):
    """إعداد مسارات التطبيق"""
    logger = logging.getLogger('silvarium_routes')

    # إعداد نظام المصادقة
    app = setup_auth(app)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        """خدمة الملفات الثابتة للتطبيق"""
        try:
            if path and os.path.exists(os.path.join(app.static_folder, path)):
                return send_from_directory(app.static_folder, path)
            return send_from_directory(app.static_folder, 'index.html')
        except Exception as e:
            logger.error(f"خطأ في خدمة الملفات الثابتة: {str(e)}")
            return jsonify({'error': 'خطأ في خدمة الملفات'}), 500

    @app.route('/api/admin/users', methods=['GET', 'POST'])
    @admin_required
    def manage_users():
        """إدارة المستخدمين - جلب القائمة وإضافة مستخدمين جدد"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            if request.method == 'GET':
                cur.execute("""
                    SELECT id, username, role, is_approved, status, created_at 
                    FROM users 
                    ORDER BY created_at DESC
                """)
                users = cur.fetchall()
                user_list = []
                for user in users:
                    user_dict = {
                        'id': user[0],
                        'username': user[1],
                        'role': user[2],
                        'isApproved': user[3],
                        'status': user[4]
                    }
                    if user[5]:  # التحقق من وجود التاريخ
                        user_dict['createdAt'] = user[5].isoformat()
                    user_list.append(user_dict)
                return jsonify(user_list)

            elif request.method == 'POST':
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'البيانات غير صالحة'}), 400

                username = data.get('username')
                password = data.get('password')
                role = data.get('role', 'user')

                if not username or not password:
                    return jsonify({'error': 'يجب توفير اسم المستخدم وكلمة المرور'}), 400

                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cur.fetchone() is not None:
                    return jsonify({'error': 'اسم المستخدم موجود بالفعل'}), 400

                hashed_password = generate_password_hash(password)
                cur.execute("""
                    INSERT INTO users (username, password, role, is_approved, status)
                    VALUES (%s, %s, %s, true, 'active')
                    RETURNING id
                """, (username, hashed_password, role))

                user_id = cur.fetchone()
                if user_id is not None:
                    user_id = user_id[0]
                    conn.commit()
                    return jsonify({
                        'message': 'تمت إضافة المستخدم بنجاح',
                        'userId': user_id
                    })
                else:
                    conn.rollback()
                    return jsonify({'error': 'فشل في إنشاء المستخدم'}), 500

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            current_app.logger.error(f"خطأ في إدارة المستخدمين: {str(e)}")
            return jsonify({'error': 'حدث خطأ في إدارة المستخدمين'}), 500
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    @app.errorhandler(404)
    def not_found_error(error):
        """معالجة أخطاء 404"""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'المسار غير موجود'}), 404
        return send_from_directory(app.static_folder, 'index.html')

    @app.errorhandler(500)
    def internal_error(error):
        """معالجة أخطاء 500"""
        return jsonify({'error': 'خطأ داخلي في الخادم'}), 500

    return app