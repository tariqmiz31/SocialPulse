from flask import Blueprint, jsonify, request
from flask_mail import Message
from functools import wraps
import secrets
import datetime
import logging
from server.database import get_db

# Setup logging
logger = logging.getLogger('silvarium')

admin_bp = Blueprint('admin', __name__)
mail = None  # Will be initialized by the application

def init_mail(mail_instance):
    """Initialize mail instance for the blueprint"""
    global mail
    mail = mail_instance

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

@admin_bp.route('/api/admin/users/<int:user_id>/<action>', methods=['POST'])
@admin_required
def modify_user(user_id, action):
    """تعديل صلاحيات المستخدم مع التحقق متعدد المراحل"""
    try:
        db = get_db()
        cursor = db.cursor()

        # التحقق من وجود المستخدم
        cursor.execute(
            """
            SELECT id, username, email, role, status 
            FROM users 
            WHERE id = %s
            """,
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({'message': 'المستخدم غير موجود'}), 404

        if action not in ['promote', 'demote', 'block', 'unblock', 'approve']:
            return jsonify({'message': 'إجراء غير صالح'}), 400

        if user[1] == 'Tariq':
            return jsonify({'message': 'لا يمكن تعديل صلاحيات المستخدم الرئيسي'}), 403

        verification_step = request.json.get('verificationStep', 'initial')
        email = request.json.get('email')

        # التحقق من المراحل
        if action in ['promote', 'demote']:
            if verification_step == 'initial':
                logger.info(f"بدء عملية تغيير صلاحيات المستخدم {user[1]}")

                if not email:
                    return jsonify({'message': 'البريد الإلكتروني مطلوب'}), 400

                # إنشاء رمز تحقق
                verification_code = ''.join(secrets.choice('0123456789') for _ in range(6))
                expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

                try:
                    # حفظ رمز التحقق
                    cursor.execute("""
                        INSERT INTO verification_codes 
                        (user_id, code, type, expires_at, created_at) 
                        VALUES (%s, %s, 'role_change', %s, NOW())
                        RETURNING id
                    """, (request.user.id, verification_code, expires_at))

                    verification_id = cursor.fetchone()[0]
                    db.commit()

                    # إرسال رمز التحقق بالبريد
                    if mail is None:
                        logger.error('Mail instance not initialized')
                        return jsonify({'message': 'خطأ في إعداد البريد الإلكتروني'}), 500

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
                    db.rollback()
                    logger.error(f'خطأ في إرسال رمز التحقق: {str(e)}')
                    return jsonify({
                        'message': 'حدث خطأ في إرسال رمز التحقق'
                    }), 500

            elif verification_step == 'email_verified':
                code = request.json.get('code')
                if not code:
                    return jsonify({'message': 'رمز التحقق مطلوب'}), 400

                # التحقق من صحة الرمز
                cursor.execute("""
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

                verification = cursor.fetchone()
                if not verification:
                    return jsonify({'message': 'رمز التحقق غير صالح أو منتهي الصلاحية'}), 400

                try:
                    # تحديث حالة الرمز
                    cursor.execute("""
                        UPDATE verification_codes 
                        SET verified = true 
                        WHERE id = %s
                    """, (verification[0],))

                    # تحديث دور المستخدم
                    new_role = 'admin' if action == 'promote' else 'user'
                    cursor.execute("""
                        UPDATE users 
                        SET role = %s, 
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING username, email
                    """, (new_role, user_id))

                    updated_user = cursor.fetchone()
                    db.commit()

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
                            <p>دورك الجديد: <strong>{'مشرف' if new_role == 'admin' else 'مستخدم'}</strong></p>
                            <br>
                            <p>مع تحيات،<br>فريق سيلفاريوم</p>
                        </div>
                        """
                        mail.send(msg)
                        logger.info(f'تم إرسال إشعار تحديث الصلاحيات إلى {updated_user[1]}')

                    return jsonify({
                        'message': f'تم تحديث صلاحيات المستخدم {updated_user[0]} بنجاح'
                    }), 200

                except Exception as e:
                    db.rollback()
                    logger.error(f'خطأ في تحديث صلاحيات المستخدم: {str(e)}')
                    return jsonify({
                        'message': 'حدث خطأ في تحديث صلاحيات المستخدم'
                    }), 500

            else:
                return jsonify({'message': 'خطوة تحقق غير صالحة'}), 400

        else:
            # باقي الإجراءات (block, unblock, approve)
            try:
                if action == 'block':
                    cursor.execute("""
                        UPDATE users 
                        SET status = 'blocked', 
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING username, email
                    """, (user_id,))
                    message = 'تم حظر المستخدم بنجاح'

                elif action == 'unblock':
                    cursor.execute("""
                        UPDATE users 
                        SET status = 'active', 
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING username, email
                    """, (user_id,))
                    message = 'تم إلغاء حظر المستخدم بنجاح'

                elif action == 'approve':
                    cursor.execute("""
                        UPDATE users 
                        SET is_approved = true,
                            status = 'active',
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING username, email
                    """, (user_id,))
                    message = 'تمت الموافقة على المستخدم بنجاح'

                updated_user = cursor.fetchone()
                db.commit()

                return jsonify({'message': message}), 200

            except Exception as e:
                db.rollback()
                logger.error(f'خطأ في تنفيذ الإجراء {action}: {str(e)}')
                return jsonify({
                    'message': f'حدث خطأ في تنفيذ الإجراء {action}'
                }), 500

    except Exception as e:
        logger.error(f'خطأ في تعديل صلاحيات المستخدم: {str(e)}')
        return jsonify({
            'message': 'حدث خطأ أثناء تعديل صلاحيات المستخدم'
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()