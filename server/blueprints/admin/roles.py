"""Role management and verification endpoints"""
from flask import Blueprint, jsonify, request, g, current_app
from flask_login import login_required, current_user
from functools import wraps
from server.blueprints.auth.verification import verification_manager
import logging
from flask_mail import Message
import secrets
import datetime

logger = logging.getLogger('silvarium_admin')
roles_bp = Blueprint('roles', __name__, url_prefix='/api/roles')

def admin_required(f):
    """للتحقق من صلاحيات المشرف"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({
                'success': False,
                'message': {
                    'ar': 'غير مصرح لك بالوصول',
                    'en': 'Unauthorized access'
                }
            }), 403
        return f(*args, **kwargs)
    return decorated_function

def verify_admin_count():
    """التحقق من عدد المشرفين قبل إلغاء صلاحيات مشرف"""
    cur = g.db.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND status = 'active'")
        admin_count = cur.fetchone()[0]
        return admin_count > 1
    finally:
        cur.close()

def send_verification_email(email, code, action, username):
    """إرسال رمز التحقق عبر البريد الإلكتروني"""
    try:
        msg = Message(
            'تأكيد تغيير الصلاحيات - سيلفاريوم',
            recipients=[email]
        )
        msg.html = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif;">
            <h2>تأكيد تغيير صلاحيات المستخدم</h2>
            <p>مرحباً،</p>
            <p>تم طلب {action} للمستخدم {username}.</p>
            <p>رمز التحقق الخاص بك هو: <strong>{code}</strong></p>
            <p>هذا الرمز صالح لمدة 10 دقائق فقط.</p>
            <p>إذا لم تقم بطلب هذا التغيير، يرجى تجاهل هذا البريد الإلكتروني وإبلاغ المسؤول.</p>
            <br>
            <p>مع تحيات،<br>فريق سيلفاريوم</p>
        </div>
        """
        current_app.mail.send(msg)
        return True
    except Exception as e:
        logger.error(f"خطأ في إرسال البريد الإلكتروني: {str(e)}")
        return False

@roles_bp.route('/change-request', methods=['POST'])
@login_required
@admin_required
def request_role_change():
    """بدء عملية تغيير صلاحيات مستخدم"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_role = data.get('new_role')
        reason = data.get('reason')
        admin_email = data.get('admin_email')

        if not all([user_id, new_role, reason, admin_email]):
            return jsonify({
                'success': False,
                'message': {
                    'ar': 'جميع الحقول مطلوبة',
                    'en': 'All fields are required'
                }
            }), 400

        # التحقق من صحة الدور الجديد
        if new_role not in ['admin', 'user']:
            return jsonify({
                'success': False,
                'message': {
                    'ar': 'الدور غير صالح',
                    'en': 'Invalid role'
                }
            }), 400

        cur = g.db.cursor()
        try:
            # التحقق من وجود المستخدم
            cur.execute("""
                SELECT username, role, email 
                FROM users 
                WHERE id = %s AND status = 'active'
            """, (user_id,))
            user = cur.fetchone()

            if not user:
                return jsonify({
                    'success': False,
                    'message': {
                        'ar': 'المستخدم غير موجود أو غير نشط',
                        'en': 'User not found or inactive'
                    }
                }), 404

            username, current_role, user_email = user

            # التحقق من عدد المشرفين عند إلغاء صلاحيات مشرف
            if current_role == 'admin' and new_role == 'user':
                if not verify_admin_count():
                    return jsonify({
                        'success': False,
                        'message': {
                            'ar': 'لا يمكن إلغاء صلاحيات المشرف الوحيد',
                            'en': 'Cannot demote the only admin'
                        }
                    }), 400

            # إنشاء رمز تحقق جديد
            verification_code = ''.join(secrets.choice('0123456789') for _ in range(6))
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

            # حفظ رمز التحقق
            cur.execute("""
                INSERT INTO verification_codes 
                (user_id, code, type, expires_at, verification_step, total_steps)
                VALUES (%s, %s, 'role_change', %s, 1, 3)
                RETURNING id
            """, (user_id, verification_code, expires_at))

            verification_id = cur.fetchone()[0]

            # تسجيل طلب تغيير الصلاحيات
            cur.execute("""
                INSERT INTO role_change_history 
                (user_id, admin_id, old_role, new_role, change_reason, 
                 verification_id, client_ip, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                current_user.id,
                current_role,
                new_role,
                reason,
                verification_id,
                request.remote_addr,
                request.user_agent.string
            ))

            # تحديث حالة المستخدم
            cur.execute("""
                UPDATE users 
                SET pending_role = %s,
                    role_change_approved = false,
                    role_change_approver_id = NULL
                WHERE id = %s
            """, (new_role, user_id))

            # إرسال رمز التحقق بالبريد
            if not send_verification_email(
                admin_email, 
                verification_code,
                'ترقية' if new_role == 'admin' else 'إلغاء صلاحيات المشرف',
                username
            ):
                cur.execute("ROLLBACK")
                return jsonify({
                    'success': False,
                    'message': {
                        'ar': 'فشل في إرسال رمز التحقق',
                        'en': 'Failed to send verification code'
                    }
                }), 500

            g.db.commit()

            return jsonify({
                'success': True,
                'message': {
                    'ar': 'تم إرسال رمز التحقق إلى بريدك الإلكتروني',
                    'en': 'Verification code sent to your email'
                },
                'verification_id': verification_id,
                'expires_at': expires_at.isoformat()
            })

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"خطأ في طلب تغيير الصلاحيات: {str(e)}")
        return jsonify({
            'success': False,
            'message': {
                'ar': 'حدث خطأ في معالجة الطلب',
                'en': 'Error processing request'
            }
        }), 500

@roles_bp.route('/verify-change', methods=['POST'])
@login_required
@admin_required
def verify_role_change():
    """التحقق من تغيير الصلاحيات"""
    try:
        data = request.get_json()
        verification_id = data.get('verification_id')
        code = data.get('code')

        if not all([verification_id, code]):
            return jsonify({
                'success': False,
                'message': {
                    'ar': 'جميع الحقول مطلوبة',
                    'en': 'All fields are required'
                }
            }), 400

        cur = g.db.cursor()
        try:
            # التحقق من صحة الرمز والخطوة
            cur.execute("""
                SELECT v.id, v.user_id, v.verification_step, v.total_steps,
                       u.username, u.pending_role, rch.old_role
                FROM verification_codes v
                JOIN users u ON v.user_id = u.id
                JOIN role_change_history rch ON v.id = rch.verification_id
                WHERE v.id = %s 
                AND v.code = %s 
                AND v.expires_at > NOW() 
                AND v.verified = false
                AND v.type = 'role_change'
            """, (verification_id, code))

            verification = cur.fetchone()
            if not verification:
                return jsonify({
                    'success': False,
                    'message': {
                        'ar': 'رمز التحقق غير صالح أو منتهي الصلاحية',
                        'en': 'Invalid or expired verification code'
                    }
                }), 400

            v_id, user_id, step, total_steps, username, new_role, old_role = verification

            # تحديث خطوة التحقق
            next_step = step + 1
            if next_step <= total_steps:
                cur.execute("""
                    UPDATE verification_codes
                    SET verification_step = %s
                    WHERE id = %s
                """, (next_step, v_id))

                g.db.commit()

                return jsonify({
                    'success': True,
                    'message': {
                        'ar': f'تم التحقق من الخطوة {step} من {total_steps}',
                        'en': f'Step {step} of {total_steps} verified'
                    },
                    'step': next_step,
                    'total_steps': total_steps
                })

            # اكتملت جميع الخطوات، تنفيذ التغيير
            cur.execute("""
                UPDATE users 
                SET role = pending_role,
                    role_change_approved = true,
                    role_change_approver_id = %s,
                    pending_role = NULL,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING email
            """, (current_user.id, user_id))

            user_email = cur.fetchone()[0]

            # تحديث سجل التغييرات
            cur.execute("""
                UPDATE role_change_history
                SET approval_status = 'approved',
                    approver_id = %s,
                    approved_at = NOW()
                WHERE verification_id = %s
            """, (current_user.id, v_id))

            # تحديث رمز التحقق
            cur.execute("""
                UPDATE verification_codes
                SET verified = true,
                    verified_at = NOW()
                WHERE id = %s
            """, (v_id,))

            # إرسال إشعار للمستخدم
            if user_email:
                msg = Message(
                    'تحديث الصلاحيات - سيلفاريوم',
                    recipients=[user_email]
                )
                msg.html = f"""
                <div dir="rtl" style="font-family: Arial, sans-serif;">
                    <h2>تم تحديث صلاحياتك في نظام سيلفاريوم</h2>
                    <p>مرحباً {username}،</p>
                    <p>تم تحديث صلاحياتك من {old_role} إلى {new_role}.</p>
                    <br>
                    <p>مع تحيات،<br>فريق سيلفاريوم</p>
                </div>
                """
                try:
                    current_app.mail.send(msg)
                except Exception as e:
                    logger.warning(f"فشل في إرسال إشعار تحديث الصلاحيات: {str(e)}")

            g.db.commit()

            return jsonify({
                'success': True,
                'message': {
                    'ar': f'تم تحديث صلاحيات المستخدم من {old_role} إلى {new_role}',
                    'en': f'User role updated from {old_role} to {new_role}'
                },
                'completed': True
            })

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"خطأ في التحقق من تغيير الصلاحيات: {str(e)}")
        return jsonify({
            'success': False,
            'message': {
                'ar': 'حدث خطأ في معالجة الطلب',
                'en': 'Error processing request'
            }
        }), 500

@roles_bp.route('/change-status/<int:verification_id>', methods=['GET'])
@login_required
@admin_required
def get_change_status(verification_id):
    """الحصول على حالة تغيير الصلاحيات"""
    try:
        cur = g.db.cursor()
        try:
            cur.execute("""
                SELECT v.verification_step, v.total_steps, v.verified,
                       u.username, u.pending_role, rch.old_role,
                       rch.approval_status
                FROM verification_codes v
                JOIN users u ON v.user_id = u.id
                JOIN role_change_history rch ON v.id = rch.verification_id
                WHERE v.id = %s AND v.type = 'role_change'
            """, (verification_id,))

            result = cur.fetchone()
            if not result:
                return jsonify({
                    'success': False,
                    'message': {
                        'ar': 'لم يتم العثور على طلب التغيير',
                        'en': 'Change request not found'
                    }
                }), 404

            step, total, verified, username, new_role, old_role, status = result

            return jsonify({
                'success': True,
                'status': {
                    'step': step,
                    'total_steps': total,
                    'completed': verified,
                    'username': username,
                    'current_role': old_role,
                    'new_role': new_role,
                    'approval_status': status
                }
            })

        finally:
            cur.close()

    except Exception as e:
        logger.error(f"خطأ في الحصول على حالة التغيير: {str(e)}")
        return jsonify({
            'success': False,
            'message': {
                'ar': 'حدث خطأ في معالجة الطلب',
                'en': 'Error processing request'
            }
        }), 500