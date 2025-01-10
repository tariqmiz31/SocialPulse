from flask import Flask, send_from_directory, jsonify, request
import os
from server.blueprints.auth import auth_bp, init_auth
from flask_mail import Message
from functools import wraps
import secrets
import datetime

def login_required(f):
    """تأكد من تسجيل دخول المستخدم"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            return jsonify({'message': 'يجب تسجيل الدخول'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """تأكد من أن المستخدم مشرف"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            return jsonify({'message': 'يجب تسجيل الدخول'}), 401
        if request.user.role != 'admin':
            return jsonify({'message': 'غير مصرح بهذا الإجراء'}), 403
        return f(*args, **kwargs)
    return decorated_function

def register_routes(app: Flask):
    """إعداد مسارات التطبيق"""
    from server.app import mail

    # تسجيل مسارات المصادقة
    app.register_blueprint(auth_bp)

    @app.route('/api/admin/users/<int:user_id>/<action>', methods=['POST'])
    @admin_required
    def modify_user(user_id, action):
        """تعديل صلاحيات المستخدم مع التحقق متعدد المراحل"""
        try:
            verification_step = request.json.get('verificationStep', 'initial')

            # التحقق من وجود المستخدم
            with app.db.cursor() as cur:
                cur.execute(
                    "SELECT * FROM users WHERE id = %s",
                    (user_id,)
                )
                user = cur.fetchone()

                if not user:
                    return jsonify({'message': 'المستخدم غير موجود'}), 404

                if action not in ['promote', 'demote']:
                    return jsonify({'message': 'إجراء غير صالح'}), 400

                # التحقق من المراحل
                if verification_step == 'initial':
                    # إنشاء رمز تحقق
                    verification_code = ''.join(secrets.choice('0123456789') for _ in range(6))
                    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

                    # حفظ رمز التحقق
                    cur.execute("""
                        INSERT INTO verification_codes (user_id, code, type, expires_at)
                        VALUES (%s, %s, 'role_change', %s)
                    """, (request.user.id, verification_code, expires_at))

                    # إرسال رمز التحقق بالبريد
                    if request.user.email:
                        msg = Message(
                            'تأكيد تغيير الصلاحيات',
                            recipients=[request.user.email]
                        )
                        msg.body = f'رمز التحقق الخاص بك هو: {verification_code}'
                        mail.send(msg)

                        return jsonify({'message': 'تم إرسال رمز التحقق'}), 200
                    else:
                        return jsonify({'message': 'البريد الإلكتروني غير متوفر'}), 400

                elif verification_step == 'email_verified':
                    code = request.json.get('code')
                    if not code:
                        return jsonify({'message': 'رمز التحقق مطلوب'}), 400

                    # التحقق من صحة الرمز
                    cur.execute("""
                        SELECT * FROM verification_codes 
                        WHERE user_id = %s AND code = %s AND type = 'role_change'
                        AND expires_at > NOW() AND verified = false
                        ORDER BY created_at DESC LIMIT 1
                    """, (request.user.id, code))

                    verification = cur.fetchone()
                    if not verification:
                        return jsonify({'message': 'رمز التحقق غير صالح'}), 400

                    # تحديث حالة الرمز
                    cur.execute("""
                        UPDATE verification_codes 
                        SET verified = true 
                        WHERE id = %s
                    """, (verification[0],))

                    # تحديث دور المستخدم
                    new_role = 'admin' if action == 'promote' else 'user'
                    cur.execute("""
                        UPDATE users 
                        SET role = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (new_role, user_id))

                    app.db.commit()
                    return jsonify({
                        'message': 'تم تحديث صلاحيات المستخدم بنجاح'
                    }), 200

                else:
                    return jsonify({'message': 'خطوة تحقق غير صالحة'}), 400

        except Exception as e:
            app.db.rollback()
            app.logger.error(f'خطأ في تعديل صلاحيات المستخدم: {str(e)}')
            return jsonify({'message': 'حدث خطأ أثناء تعديل صلاحيات المستخدم'}), 500

    # المسار الرئيسي وخدمة الملفات الثابتة
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        """خدمة الملفات الثابتة للتطبيق"""
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    # معالجة الأخطاء
    @app.errorhandler(404)
    def not_found_error(error):
        """معالجة أخطاء 404"""
        if request.path.startswith('/api/'):
            return jsonify({
                'message': {
                    'ar': 'المسار غير موجود',
                    'en': 'Path not found'
                }
            }), 404

        index_path = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, 'index.html')
        else:
            return jsonify({
                'message': {
                    'ar': 'الصفحة غير موجودة',
                    'en': 'Page not found'
                }
            }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """معالجة أخطاء 500"""
        return jsonify({
            'message': {
                'ar': 'خطأ داخلي في الخادم',
                'en': 'Internal server error'
            }
        }), 500

    return app