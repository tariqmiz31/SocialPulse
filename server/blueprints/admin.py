from flask import Blueprint, jsonify, request, session
from flask_mail import Message
from flask_login import login_required, current_user
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
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'message': 'يجب تسجيل الدخول'}), 401
        if current_user.role != 'admin':
            return jsonify({'message': 'غير مصرح بهذا الإجراء'}), 403
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/api/admin/users/<int:user_id>/<action>', methods=['POST'])
@admin_required
def modify_user(user_id, action):
    """تعديل صلاحيات المستخدم مع التحقق متعدد المراحل"""
    try:
        # Get database connection
        db = get_db()
        if not db:
            logger.error("فشل في الاتصال بقاعدة البيانات")
            return jsonify({'message': 'خطأ في الاتصال بقاعدة البيانات'}), 500

        cursor = db.cursor()
        try:
            # التحقق من وجود المستخدم
            cursor.execute("""
                SELECT id, username, email, role, status 
                FROM users 
                WHERE id = %s
            """, (user_id,))
            user = cursor.fetchone()

            if not user:
                return jsonify({'message': 'المستخدم غير موجود'}), 404

            if action not in ['promote', 'demote', 'block', 'unblock', 'approve', 'delete']:
                return jsonify({'message': 'إجراء غير صالح'}), 400

            if user[1] == 'Tariq':  # التحقق من اسم المستخدم
                return jsonify({'message': 'لا يمكن تعديل صلاحيات المستخدم الرئيسي'}), 403

            verification_step = request.json.get('verificationStep', 'initial')
            email = request.json.get('email')

            # التحقق من المراحل لتغيير الصلاحيات
            if action in ['promote', 'demote']:
                if verification_step == 'initial':
                    logger.info(f"بدء عملية تغيير صلاحيات المستخدم {user[1]}")

                    if not email:
                        return jsonify({'message': 'البريد الإلكتروني مطلوب للتحقق'}), 400

                    # التحقق من عدد محاولات التحقق
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM verification_attempts 
                        WHERE email = %s 
                        AND attempt_time > NOW() - INTERVAL '1 hour'
                    """, (email,))
                    attempt_count = cursor.fetchone()[0]

                    if attempt_count >= 5:
                        return jsonify({'message': 'تم تجاوز الحد الأقصى لمحاولات التحقق. الرجاء المحاولة لاحقاً'}), 429

                    # تسجيل محاولة التحقق
                    cursor.execute("""
                        INSERT INTO verification_attempts (email, attempt_time)
                        VALUES (%s, NOW())
                    """, (email,))

                    # إنشاء رمز تحقق
                    verification_code = ''.join(secrets.choice('0123456789') for _ in range(6))
                    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

                    # حفظ رمز التحقق
                    cursor.execute("""
                        INSERT INTO verification_codes 
                        (user_id, code, type, expires_at, created_at) 
                        VALUES (%s, %s, 'role_change', %s, NOW())
                        RETURNING id
                    """, (current_user.id, verification_code, expires_at))

                    verification_id = cursor.fetchone()[0]

                    # حفظ معلومات في الجلسة
                    session['verification_id'] = verification_id
                    session['role_change_action'] = action
                    session['target_user_id'] = user_id

                    # إرسال رمز التحقق بالبريد
                    if not mail:
                        logger.error('لم يتم تهيئة خدمة البريد')
                        db.rollback()
                        return jsonify({'message': 'خطأ في إعداد البريد الإلكتروني'}), 500

                    try:
                        msg = Message(
                            'رمز التحقق لتغيير الصلاحيات - سيلفاريوم',
                            recipients=[email]
                        )
                        msg.html = f"""
                        <div dir="rtl" style="font-family: Arial, sans-serif;">
                            <h2>تأكيد تغيير صلاحيات المستخدم</h2>
                            <p>مرحباً،</p>
                            <p>لقد تلقينا طلباً لتغيير صلاحيات مستخدم في نظام سيلفاريوم.</p>
                            <p>رمز التحقق الخاص بك هو: <strong>{verification_code}</strong></p>
                            <p>هذا الرمز صالح لمدة 10 دقائق فقط.</p>
                            <p>إذا لم تقم بطلب هذا التغيير، يرجى تجاهل هذا البريد الإلكتروني وإبلاغ المسؤول.</p>
                            <br>
                            <p>مع تحيات،<br>فريق سيلفاريوم</p>
                        </div>
                        """
                        mail.send(msg)
                        db.commit()
                        logger.info(f'تم إرسال رمز التحقق إلى {email}')

                        return jsonify({
                            'message': 'تم إرسال رمز التحقق إلى بريدك الإلكتروني',
                            'expiry': expires_at.isoformat()
                        }), 200

                    except Exception as e:
                        logger.error(f'خطأ في إرسال البريد الإلكتروني: {str(e)}')
                        db.rollback()
                        return jsonify({'message': 'حدث خطأ في إرسال رمز التحقق'}), 500

                elif verification_step == 'verify_code':
                    if 'verification_id' not in session:
                        return jsonify({'message': 'جلسة التحقق غير صالحة'}), 400

                    verification_code = request.json.get('code')
                    if not verification_code:
                        return jsonify({'message': 'رمز التحقق مطلوب'}), 400

                    # التحقق من صحة الرمز
                    cursor.execute("""
                        SELECT id 
                        FROM verification_codes 
                        WHERE id = %s 
                        AND code = %s 
                        AND expires_at > NOW() 
                        AND verified = false
                        AND type = 'role_change'
                    """, (session['verification_id'], verification_code))

                    verification = cursor.fetchone()
                    if not verification:
                        return jsonify({'message': 'رمز التحقق غير صحيح أو منتهي الصلاحية'}), 400

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

                        # تسجيل التغيير في السجل
                        cursor.execute("""
                            INSERT INTO role_change_history 
                            (user_id, admin_id, old_role, new_role, verification_id, created_at)
                            VALUES (%s, %s, %s, %s, %s, NOW())
                        """, (user_id, current_user.id, user[3], new_role, verification[0]))

                        # مسح معلومات التحقق من الجلسة
                        session.pop('verification_id', None)
                        session.pop('role_change_action', None)
                        session.pop('target_user_id', None)

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
                            try:
                                mail.send(msg)
                                logger.info(f'تم إرسال إشعار تحديث الصلاحيات إلى {updated_user[1]}')
                            except Exception as e:
                                logger.warning(f'فشل في إرسال إشعار تحديث الصلاحيات: {str(e)}')

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
                # باقي الإجراءات (block, unblock, approve, delete)
                try:
                    message = None
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

                    elif action == 'delete':
                        cursor.execute("""
                            UPDATE users 
                            SET status = 'deleted',
                                updated_at = NOW()
                            WHERE id = %s
                            RETURNING username, email
                        """, (user_id,))
                        message = 'تم حذف المستخدم بنجاح'

                    updated_user = cursor.fetchone()
                    db.commit()

                    if updated_user and updated_user[1]:  # إرسال إشعار للمستخدم
                        try:
                            msg = Message(
                                'تحديث حالة الحساب - سيلفاريوم',
                                recipients=[updated_user[1]]
                            )
                            msg.html = f"""
                            <div dir="rtl" style="font-family: Arial, sans-serif;">
                                <h2>تم تحديث حالة حسابك في سيلفاريوم</h2>
                                <p>مرحباً {updated_user[0]}،</p>
                                <p>{message}</p>
                                <br>
                                <p>مع تحيات،<br>فريق سيلفاريوم</p>
                            </div>
                            """
                            mail.send(msg)
                            logger.info(f'تم إرسال إشعار تحديث الحالة إلى {updated_user[1]}')
                        except Exception as e:
                            logger.warning(f'فشل في إرسال إشعار تحديث الحالة: {str(e)}')

                    return jsonify({'message': message}), 200

                except Exception as e:
                    db.rollback()
                    logger.error(f'خطأ في تنفيذ الإجراء {action}: {str(e)}')
                    return jsonify({
                        'message': f'حدث خطأ في تنفيذ الإجراء {action}'
                    }), 500

        finally:
            cursor.close()

    except Exception as e:
        logger.error(f'خطأ في تعديل صلاحيات المستخدم: {str(e)}')
        return jsonify({
            'message': 'حدث خطأ أثناء تعديل صلاحيات المستخدم'
        }), 500