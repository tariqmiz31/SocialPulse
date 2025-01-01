from flask import Flask, send_from_directory, jsonify
import os
from auth import login_required, admin_required

def setup_routes(app: Flask):
    """إعداد مسارات التطبيق"""

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        """خدمة الملفات الثابتة للتطبيق"""
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/api/admin/users', methods=['GET'])
    @admin_required
    def get_users():
        """الحصول على قائمة المستخدمين"""
        try:
            cursor = app.db.cursor()
            cursor.execute("""
                SELECT id, username, role, is_approved, status, created_at 
                FROM users 
                ORDER BY created_at DESC
            """)
            users = cursor.fetchall()
            cursor.close()

            return jsonify([{
                'id': user[0],
                'username': user[1],
                'role': user[2],
                'isApproved': user[3],
                'status': user[4],
                'createdAt': user[5].isoformat() if user[5] else None
            } for user in users])
        except Exception as e:
            app.logger.error(f"Error fetching users: {e}")
            return jsonify({'error': 'حدث خطأ في جلب بيانات المستخدمين'}), 500

    return app