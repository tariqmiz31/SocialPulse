from flask import Flask, send_from_directory, jsonify, request
import os
from flask_mail import Message, Mail
from functools import wraps
import secrets
import datetime
import logging

# Initialize Flask-Mail and logger
mail = Mail()
logger = logging.getLogger('silvarium')

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

def register_routes(app: Flask) -> Flask:
    """تسجيل مسارات التطبيق"""
    # تهيئة خدمة البريد الإلكتروني
    mail.init_app(app)

    @app.route('/api/admin/users/<int:user_id>/<action>', methods=['POST'])
    @admin_required
    def modify_user(user_id, action):
        """تعديل صلاحيات المستخدم مع التحقق متعدد المراحل"""
        try:
            verification_step = request.json.get('verificationStep', 'initial')
            email = request.json.get('email')

            # التحقق من وجود المستخدم
            with app.db.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, username, email, role, status 
                    FROM users 
                    WHERE id = %s
                    """,
                    (user_id,)
                )
                user = cur.fetchone()

                if not user:
                    return jsonify({'message': 'المستخدم غير موجود'}), 404

                if action not in ['promote', 'demote']:
                    return jsonify({'message': 'إجراء غير صالح'}), 400

                if user[1] == 'Tariq':
                    return jsonify({'message': 'لا يمكن تعديل صلاحيات المستخدم الرئيسي'}), 403

                # التحقق من المراحل
                if verification_step == 'initial':
                    if not email:
                        return jsonify({'message': 'البريد الإلكتروني مطلوب'}), 400

                    # إنشاء رمز تحقق
                    verification_code = ''.join(secrets.choice('0123456789') for _ in range(6))
                    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

                    try:
                        # حفظ رمز التحقق
                        cur.execute("""
                            INSERT INTO verification_codes 
                            (user_id, code, type, expires_at, created_at) 
                            VALUES (%s, %s, 'role_change', %s, NOW())
                            RETURNING id
                        """, (request.user.id, verification_code, expires_at))

                        verification_id = cur.fetchone()[0]
                        app.db.commit()

                        # إرسال رمز التحقق بالبريد
                        msg = Message(
                            'تأكيد تغيير الصلاحيات - سيلفاريوم',
                            recipients=[email]
                        )
                        msg.html = f"""
                        <div dir="rtl" style="font-family: Arial, sans-serif;">
                            <h2>تأكيد تغيير صلاحيات المستخدم</h2>
                            <p>مرحباً،</p>
                            <p>لقد تلقينا طلباً لتغيير صلاحيات مستخدم في نظام سيلفاريوم.</p>
                            <p>رمز التحقق الخاص بك هو: <strong>{verification_code}</strong></p>
                            <p>هذا الرمز صالح لمدة 10 دقائق فقط.</p>
                            <p>إذا لم تقم بطلب هذا التغيير، يرجى تجاهل هذا البريد الإلكتروني.</p>
                            <br>
                            <p>مع تحيات،<br>فريق سيلفاريوم</p>
                        </div>
                        """
                        mail.send(msg)
                        logger.info(f'تم إرسال رمز التحقق إلى {email}')

                        return jsonify({
                            'message': 'تم إرسال رمز التحقق إلى بريدك الإلكتروني'
                        }), 200

                    except Exception as e:
                        app.db.rollback()
                        logger.error(f'خطأ في إرسال رمز التحقق: {str(e)}')
                        return jsonify({
                            'message': 'حدث خطأ في إرسال رمز التحقق'
                        }), 500

                elif verification_step == 'email_verified':
                    code = request.json.get('code')
                    if not code:
                        return jsonify({'message': 'رمز التحقق مطلوب'}), 400

                    # التحقق من صحة الرمز
                    cur.execute("""
                        SELECT id 
                        FROM verification_codes 
                        WHERE user_id = %s 
                        AND code = %s 
                        AND type = 'role_change'
                        AND expires_at > NOW() 
                        AND verified = false
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """, (request.user.id, code))

                    verification = cur.fetchone()
                    if not verification:
                        return jsonify({'message': 'رمز التحقق غير صالح أو منتهي الصلاحية'}), 400

                    try:
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
                            SET role = %s, 
                                updated_at = NOW()
                            WHERE id = %s
                            RETURNING username, email
                        """, (new_role, user_id))

                        updated_user = cur.fetchone()
                        app.db.commit()

                        # إرسال إشعار للمستخدم
                        if updated_user[1]:  # إذا كان لديه بريد إلكتروني
                            msg = Message(
                                'تحديث الصلاحيات - سيلفاريوم',
                                recipients=[updated_user[1]]
                            )
                            msg.html = f"""
                            <div dir="rtl" style="font-family: Arial, sans-serif;">
                                <h2>تم تحديث صلاحياتك في نظام سيلفاريوم</h2>
                                <p>مرحباً {updated_user[0]}،</p>
                                <p>نود إعلامك أنه تم تحديث صلاحياتك في نظام سيلفاريوم.</p>
                                <p>دورك الجديد: <strong>{new_role}</strong></p>
                                <br>
                                <p>مع تحيات،<br>فريق سيلفاريوم</p>
                            </div>
                            """
                            mail.send(msg)

                        return jsonify({
                            'message': f'تم تحديث صلاحيات المستخدم {updated_user[0]} بنجاح'
                        }), 200

                    except Exception as e:
                        app.db.rollback()
                        logger.error(f'خطأ في تحديث صلاحيات المستخدم: {str(e)}')
                        return jsonify({
                            'message': 'حدث خطأ في تحديث صلاحيات المستخدم'
                        }), 500

                else:
                    return jsonify({'message': 'خطوة تحقق غير صالحة'}), 400

        except Exception as e:
            logger.error(f'خطأ في تعديل صلاحيات المستخدم: {str(e)}')
            return jsonify({
                'message': 'حدث خطأ أثناء تعديل صلاحيات المستخدم'
            }), 500

    # المسار الرئيسي وخدمة الملفات الثابتة
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        """خدمة الملفات الثابتة للتطبيق"""
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    return app