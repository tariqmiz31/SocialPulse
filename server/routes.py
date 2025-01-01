from flask import Flask, send_from_directory, jsonify, request
import os
from auth import login_required, admin_required
import psycopg2
from datetime import datetime

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
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                SELECT id, username, role, is_approved, status, created_at 
                FROM users 
                ORDER BY created_at DESC
            """)
            users = cur.fetchall()

            cur.close()
            conn.close()

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

    @app.route('/api/admin/users/<int:user_id>/approve', methods=['POST'])
    @admin_required
    def approve_user(user_id):
        """الموافقة على المستخدم"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                UPDATE users 
                SET is_approved = true, status = 'active' 
                WHERE id = %s
                RETURNING id
            """, (user_id,))

            updated = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()

            if updated:
                return jsonify({'message': 'تمت الموافقة على المستخدم بنجاح'})
            return jsonify({'error': 'المستخدم غير موجود'}), 404

        except Exception as e:
            app.logger.error(f"Error approving user: {e}")
            return jsonify({'error': 'حدث خطأ في تحديث حالة المستخدم'}), 500

    @app.route('/api/admin/users/<int:user_id>/block', methods=['POST'])
    @admin_required
    def block_user(user_id):
        """حظر المستخدم"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                UPDATE users 
                SET status = 'blocked' 
                WHERE id = %s
                RETURNING id
            """, (user_id,))

            updated = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()

            if updated:
                return jsonify({'message': 'تم حظر المستخدم بنجاح'})
            return jsonify({'error': 'المستخدم غير موجود'}), 404

        except Exception as e:
            app.logger.error(f"Error blocking user: {e}")
            return jsonify({'error': 'حدث خطأ في تحديث حالة المستخدم'}), 500

    @app.route('/api/admin/users/<int:user_id>/unblock', methods=['POST'])
    @admin_required
    def unblock_user(user_id):
        """إلغاء حظر المستخدم"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                UPDATE users 
                SET status = 'active' 
                WHERE id = %s
                RETURNING id
            """, (user_id,))

            updated = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()

            if updated:
                return jsonify({'message': 'تم إلغاء حظر المستخدم بنجاح'})
            return jsonify({'error': 'المستخدم غير موجود'}), 404

        except Exception as e:
            app.logger.error(f"Error unblocking user: {e}")
            return jsonify({'error': 'حدث خطأ في تحديث حالة المستخدم'}), 500

    return app