from flask import Flask, send_from_directory, jsonify, request
import os
from auth import login_required, admin_required
import psycopg2
from datetime import datetime
from werkzeug.security import generate_password_hash

def setup_routes(app: Flask):
    """إعداد مسارات التطبيق"""

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        """خدمة الملفات الثابتة للتطبيق"""
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

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

                return jsonify([{
                    'id': user[0],
                    'username': user[1],
                    'role': user[2],
                    'isApproved': user[3],
                    'status': user[4],
                    'createdAt': user[5].isoformat() if user[5] else None
                } for user in users])

            elif request.method == 'POST':
                data = request.json
                username = data.get('username')
                password = data.get('password')
                role = data.get('role', 'user')

                if not username or not password:
                    return jsonify({'error': 'يجب توفير اسم المستخدم وكلمة المرور'}), 400

                # التحقق من وجود المستخدم
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cur.fetchone():
                    return jsonify({'error': 'اسم المستخدم موجود بالفعل'}), 400

                # إضافة المستخدم الجديد
                hashed_password = generate_password_hash(password)
                cur.execute("""
                    INSERT INTO users (username, password, role, is_approved, status)
                    VALUES (%s, %s, %s, true, 'active')
                    RETURNING id
                """, (username, hashed_password, role))

                user_id = cur.fetchone()[0]
                conn.commit()

                return jsonify({
                    'message': 'تمت إضافة المستخدم بنجاح',
                    'userId': user_id
                })

        except Exception as e:
            app.logger.error(f"خطأ في إدارة المستخدمين: {e}")
            return jsonify({'error': 'حدث خطأ في إدارة المستخدمين'}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/api/admin/users/<int:user_id>/approve', methods=['POST'])
    @admin_required
    def approve_user(user_id):
        """الموافقة على المستخدم"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                UPDATE users 
                SET is_approved = true, status = 'active', updated_at = NOW()
                WHERE id = %s AND username != 'Tariq'
                RETURNING id
            """, (user_id,))

            updated = cur.fetchone()
            conn.commit()

            if updated:
                return jsonify({'message': 'تمت الموافقة على المستخدم بنجاح'})
            return jsonify({'error': 'لا يمكن تعديل حساب المشرف الرئيسي'}), 403

        except Exception as e:
            app.logger.error(f"خطأ في الموافقة على المستخدم: {e}")
            return jsonify({'error': 'حدث خطأ في تحديث حالة المستخدم'}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/api/admin/users/<int:user_id>/block', methods=['POST'])
    @admin_required
    def block_user(user_id):
        """حظر المستخدم"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                UPDATE users 
                SET status = 'blocked', updated_at = NOW()
                WHERE id = %s AND username != 'Tariq'
                RETURNING id
            """, (user_id,))

            updated = cur.fetchone()
            conn.commit()

            if updated:
                return jsonify({'message': 'تم حظر المستخدم بنجاح'})
            return jsonify({'error': 'لا يمكن حظر حساب المشرف الرئيسي'}), 403

        except Exception as e:
            app.logger.error(f"خطأ في حظر المستخدم: {e}")
            return jsonify({'error': 'حدث خطأ في تحديث حالة المستخدم'}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/api/admin/users/<int:user_id>/unblock', methods=['POST'])
    @admin_required
    def unblock_user(user_id):
        """إلغاء حظر المستخدم"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                UPDATE users 
                SET status = 'active', updated_at = NOW()
                WHERE id = %s AND username != 'Tariq'
                RETURNING id
            """, (user_id,))

            updated = cur.fetchone()
            conn.commit()

            if updated:
                return jsonify({'message': 'تم إلغاء حظر المستخدم بنجاح'})
            return jsonify({'error': 'لا يمكن تعديل حساب المشرف الرئيسي'}), 403

        except Exception as e:
            app.logger.error(f"خطأ في إلغاء حظر المستخدم: {e}")
            return jsonify({'error': 'حدث خطأ في تحديث حالة المستخدم'}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/api/admin/users/<int:user_id>/promote', methods=['POST'])
    @admin_required
    def promote_user(user_id):
        """ترقية المستخدم إلى مشرف"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                UPDATE users 
                SET role = 'admin', updated_at = NOW()
                WHERE id = %s AND username != 'Tariq'
                RETURNING id
            """, (user_id,))

            updated = cur.fetchone()
            conn.commit()

            if updated:
                return jsonify({'message': 'تمت ترقية المستخدم إلى مشرف بنجاح'})
            return jsonify({'error': 'لا يمكن تعديل حساب المشرف الرئيسي'}), 403

        except Exception as e:
            app.logger.error(f"خطأ في ترقية المستخدم: {e}")
            return jsonify({'error': 'حدث خطأ في تحديث صلاحيات المستخدم'}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/api/admin/users/<int:user_id>/demote', methods=['POST'])
    @admin_required
    def demote_user(user_id):
        """إلغاء صلاحيات الإشراف"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                UPDATE users 
                SET role = 'user', updated_at = NOW()
                WHERE id = %s AND username != 'Tariq'
                RETURNING id
            """, (user_id,))

            updated = cur.fetchone()
            conn.commit()

            if updated:
                return jsonify({'message': 'تم إلغاء صلاحيات الإشراف بنجاح'})
            return jsonify({'error': 'لا يمكن تعديل حساب المشرف الرئيسي'}), 403

        except Exception as e:
            app.logger.error(f"خطأ في إلغاء صلاحيات الإشراف: {e}")
            return jsonify({'error': 'حدث خطأ في تحديث صلاحيات المستخدم'}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/api/admin/users/<int:user_id>/delete', methods=['POST'])
    @admin_required
    def delete_user(user_id):
        """حذف المستخدم"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                DELETE FROM users
                WHERE id = %s AND username != 'Tariq'
                RETURNING id
            """, (user_id,))

            deleted = cur.fetchone()
            conn.commit()

            if deleted:
                return jsonify({'message': 'تم حذف المستخدم بنجاح'})
            return jsonify({'error': 'لا يمكن حذف حساب المشرف الرئيسي'}), 403

        except Exception as e:
            app.logger.error(f"خطأ في حذف المستخدم: {e}")
            return jsonify({'error': 'حدث خطأ في حذف المستخدم'}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/api/platforms', methods=['GET', 'POST'])
    @login_required
    def manage_platforms():
        """إدارة منصات التواصل الاجتماعي"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            if request.method == 'GET':
                cur.execute("""
                    SELECT id, name, active
                    FROM social_platforms
                    ORDER BY name ASC
                """)
                platforms = cur.fetchall()

                return jsonify([{
                    'id': platform[0],
                    'name': platform[1],
                    'active': platform[2],
                } for platform in platforms])

            elif request.method == 'POST':
                data = request.json
                name = data.get('name')
                api_key = data.get('apiKey')
                api_secret = data.get('apiSecret')

                if not name:
                    return jsonify({'error': 'اسم المنصة مطلوب'}), 400

                cur.execute("""
                    INSERT INTO social_platforms (name, api_key, api_secret)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (name, api_key, api_secret))

                platform_id = cur.fetchone()[0]
                conn.commit()

                return jsonify({
                    'message': 'تمت إضافة المنصة بنجاح',
                    'platformId': platform_id
                })

        except Exception as e:
            app.logger.error(f"خطأ في إدارة المنصات: {e}")
            return jsonify({'error': 'حدث خطأ في إدارة المنصات'}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/api/tasks', methods=['GET', 'POST'])
    @login_required
    def manage_tasks():
        """إدارة المهام والمنشورات"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            if request.method == 'GET':
                cur.execute("""
                    SELECT id, title, description, content, platform_ids, 
                           scheduled_time, status, created_at
                    FROM tasks
                    WHERE user_id = %s
                    ORDER BY scheduled_time DESC
                """, (request.user.id,))
                tasks = cur.fetchall()

                return jsonify([{
                    'id': task[0],
                    'title': task[1],
                    'description': task[2],
                    'content': task[3],
                    'platformIds': task[4],
                    'scheduledTime': task[5].isoformat() if task[5] else None,
                    'status': task[6],
                    'createdAt': task[7].isoformat() if task[7] else None,
                } for task in tasks])

            elif request.method == 'POST':
                data = request.json
                title = data.get('title')
                description = data.get('description', '')
                content = data.get('content')
                platform_ids = data.get('platformIds', [])
                scheduled_time = data.get('scheduledTime')

                if not title or not content or not platform_ids:
                    return jsonify({
                        'error': 'العنوان والمحتوى والمنصات مطلوبة'
                    }), 400

                cur.execute("""
                    INSERT INTO tasks (
                        title, description, content, platform_ids,
                        scheduled_time, user_id, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'scheduled')
                    RETURNING id
                """, (
                    title, description, content, platform_ids,
                    scheduled_time, request.user.id
                ))

                task_id = cur.fetchone()[0]
                conn.commit()

                return jsonify({
                    'message': 'تمت إضافة المهمة بنجاح',
                    'taskId': task_id
                })

        except Exception as e:
            app.logger.error(f"خطأ في إدارة المهام: {e}")
            return jsonify({'error': 'حدث خطأ في إدارة المهام'}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/api/tasks/<int:task_id>', methods=['PUT', 'DELETE'])
    @login_required
    def manage_task(task_id):
        """إدارة مهمة محددة"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            # التحقق من ملكية المهمة
            cur.execute("""
                SELECT user_id FROM tasks WHERE id = %s
            """, (task_id,))
            task = cur.fetchone()

            if not task or task[0] != request.user.id:
                return jsonify({'error': 'غير مصرح بالوصول إلى هذه المهمة'}), 403

            if request.method == 'PUT':
                data = request.json
                cur.execute("""
                    UPDATE tasks
                    SET title = %s,
                        description = %s,
                        content = %s,
                        platform_ids = %s,
                        scheduled_time = %s,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                """, (
                    data.get('title'),
                    data.get('description'),
                    data.get('content'),
                    data.get('platformIds'),
                    data.get('scheduledTime'),
                    task_id,
                    request.user.id
                ))

                updated = cur.fetchone()
                conn.commit()

                if updated:
                    return jsonify({'message': 'تم تحديث المهمة بنجاح'})
                return jsonify({'error': 'فشل تحديث المهمة'}), 400

            elif request.method == 'DELETE':
                cur.execute("""
                    DELETE FROM tasks
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                """, (task_id, request.user.id))

                deleted = cur.fetchone()
                conn.commit()

                if deleted:
                    return jsonify({'message': 'تم حذف المهمة بنجاح'})
                return jsonify({'error': 'فشل حذف المهمة'}), 400

        except Exception as e:
            app.logger.error(f"خطأ في إدارة المهمة: {e}")
            return jsonify({'error': 'حدث خطأ في إدارة المهمة'}), 500
        finally:
            cur.close()
            conn.close()

    return app