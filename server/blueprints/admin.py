from flask import Blueprint, jsonify, request, session, g, current_app
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
    def decorated_function(*args, **kwargs):
        # 1. التحقق من تسجيل الدخول
        if not current_user.is_authenticated:
            logger.warning(f"محاولة وصول غير مصرح بها: المستخدم غير مسجل الدخول")
            return jsonify({
                'status': 'error',
                'message': 'يجب تسجيل الدخول للوصول إلى هذه الصفحة',
                'code': 'unauthorized'
            }), 401

        # 2. التحقق من صلاحيات المشرف
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            logger.warning(f"محاولة وصول غير مصرح بها: المستخدم {current_user.username} ليس مشرفاً")
            return jsonify({
                'status': 'error',
                'message': 'غير مصرح بهذا الإجراء - يجب أن تكون مشرفاً',
                'code': 'forbidden'
            }), 403

        # 3. تنفيذ الوظيفة المطلوبة
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"خطأ في تنفيذ إجراء المشرف: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': 'حدث خطأ أثناء تنفيذ الإجراء',
                'code': 'internal_error'
            }), 500

    return decorated_function

@admin_bp.route('/api/admin/users/<int:user_id>/<action>', methods=['POST'])
@admin_required
def modify_user(user_id, action):
    """تعديل صلاحيات المستخدم مع التحقق متعدد المراحل وتسجيل التغييرات"""
    try:
        # Get database connection
        db = get_db()
        if not db:
            logger.error("فشل في الاتصال بقاعدة البيانات")
            return jsonify({
                'status': 'error',
                'message': 'خطأ في الاتصال بقاعدة البيانات',
                'code': 'db_error'
            }), 500

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
                logger.warning(f"محاولة تعديل مستخدم غير موجود: ID {user_id}")
                return jsonify({
                    'status': 'error',
                    'message': 'المستخدم غير موجود',
                    'code': 'not_found'
                }), 404

            if action not in ['promote', 'demote', 'block', 'unblock', 'approve', 'delete']:
                logger.warning(f"محاولة تنفيذ إجراء غير صالح: {action}")
                return jsonify({
                    'status': 'error',
                    'message': 'إجراء غير صالح',
                    'code': 'invalid_action'
                }), 400

            # التحقق من محاولة تعديل المستخدم الرئيسي
            if user[1] == 'Tariq':  # التحقق من اسم المستخدم
                logger.warning(f"محاولة تعديل صلاحيات المستخدم الرئيسي")
                return jsonify({
                    'status': 'error',
                    'message': 'لا يمكن تعديل صلاحيات المستخدم الرئيسي',
                    'code': 'forbidden'
                }), 403

            verification_step = request.json.get('verificationStep', 'initial')
            email = request.json.get('email')
            change_reason = request.json.get('reason')

            # التحقق من المراحل لتغيير الصلاحيات
            if action in ['promote', 'demote']:
                if not change_reason:
                    return jsonify({
                        'status': 'error',
                        'message': 'يجب تحديد سبب تغيير الصلاحيات',
                        'code': 'missing_reason'
                    }), 400

                # المرحلة الأولى: إرسال رمز التحقق
                if verification_step == 'initial':
                    if not email:
                        return jsonify({
                            'status': 'error',
                            'message': 'البريد الإلكتروني مطلوب للتحقق',
                            'code': 'missing_email'
                        }), 400

                    # التحقق من عدد محاولات التحقق
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM verification_attempts 
                        WHERE email = %s 
                        AND attempt_time > NOW() - INTERVAL '1 hour'
                    """, (email,))
                    attempt_count = cursor.fetchone()[0]

                    if attempt_count >= 5:
                        logger.warning(f"تم تجاوز عدد محاولات التحقق للبريد {email}")
                        return jsonify({
                            'status': 'error',
                            'message': 'تم تجاوز الحد الأقصى لمحاولات التحقق. الرجاء المحاولة لاحقاً',
                            'code': 'too_many_attempts'
                        }), 429

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
                    session.modified = True

                    # تسجيل محاولة التحقق
                    cursor.execute("""
                        INSERT INTO verification_attempts (email, attempt_time)
                        VALUES (%s, NOW())
                    """, (email,))

                    # إرسال رمز التحقق بالبريد
                    try:
                        msg = Message(
                            'رمز التحقق لتغيير الصلاحيات - سيلفاريوم',
                            recipients=[email]
                        )
                        msg.html = f"""
                        <div dir="rtl" style="font-family: Arial, sans-serif;">
                            <h2>تأكيد تغيير صلاحيات المستخدم</h2>
                            <p>مرحباً {current_user.username}،</p>
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
                            'status': 'success',
                            'message': 'تم إرسال رمز التحقق إلى بريدك الإلكتروني',
                            'expiry': expires_at.isoformat()
                        }), 200

                    except Exception as e:
                        logger.error(f'خطأ في إرسال البريد الإلكتروني: {str(e)}')
                        db.rollback()
                        return jsonify({
                            'status': 'error',
                            'message': 'حدث خطأ في إرسال رمز التحقق',
                            'code': 'email_error'
                        }), 500

                # المرحلة الثانية: التحقق من الرمز
                elif verification_step == 'verify_code':
                    if 'verification_id' not in session:
                        logger.warning('محاولة تحقق بدون جلسة صالحة')
                        return jsonify({
                            'status': 'error',
                            'message': 'جلسة التحقق غير صالحة',
                            'code': 'invalid_session'
                        }), 400

                    verification_code = request.json.get('code')
                    if not verification_code:
                        return jsonify({
                            'status': 'error',
                            'message': 'رمز التحقق مطلوب',
                            'code': 'missing_code'
                        }), 400

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
                        logger.warning(f'محاولة تحقق فاشلة: رمز غير صالح أو منتهي الصلاحية')
                        return jsonify({
                            'status': 'error',
                            'message': 'رمز التحقق غير صحيح أو منتهي الصلاحية',
                            'code': 'invalid_code'
                        }), 400

                    try:
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

                        # تسجيل التغيير في السجل مع معلومات إضافية
                        cursor.execute("""
                            INSERT INTO role_change_history 
                            (user_id, admin_id, old_role, new_role, verification_id, 
                             change_reason, client_ip, user_agent, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            user_id, 
                            current_user.id, 
                            user[3], 
                            new_role, 
                            session['verification_id'],
                            change_reason,
                            request.remote_addr,
                            request.user_agent.string
                        ))

                        # مسح معلومات التحقق من الجلسة
                        session.pop('verification_id', None)
                        session.pop('role_change_action', None)
                        session.pop('target_user_id', None)
                        session.modified = True

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
                                <p>سبب التغيير: {change_reason}</p>
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
                            'status': 'success',
                            'message': f'تم تحديث صلاحيات المستخدم {updated_user[0]} بنجاح'
                        }), 200

                    except Exception as e:
                        db.rollback()
                        logger.error(f'خطأ في تحديث صلاحيات المستخدم: {str(e)}')
                        return jsonify({
                            'status': 'error',
                            'message': 'حدث خطأ في تحديث صلاحيات المستخدم',
                            'code': 'update_error'
                        }), 500

                else:
                    logger.warning(f'خطوة تحقق غير صالحة: {verification_step}')
                    return jsonify({
                        'status': 'error',
                        'message': 'خطوة تحقق غير صالحة',
                        'code': 'invalid_step'
                    }), 400

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

                    return jsonify({
                        'status': 'success',
                        'message': message
                    }), 200

                except Exception as e:
                    db.rollback()
                    logger.error(f'خطأ في تنفيذ الإجراء {action}: {str(e)}')
                    return jsonify({
                        'status': 'error',
                        'message': f'حدث خطأ في تنفيذ الإجراء {action}',
                        'code': 'action_error'
                    }), 500

        finally:
            cursor.close()

    except Exception as e:
        logger.error(f'خطأ في تعديل صلاحيات المستخدم: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ أثناء تعديل صلاحيات المستخدم',
            'code': 'internal_error'
        }), 500