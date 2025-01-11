"""Role management and verification endpoints"""
from flask import Blueprint, jsonify, request, g
from flask_login import login_required, current_user
from functools import wraps
from server.blueprints.auth.verification import verification_manager
import logging

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
        
        if not all([user_id, new_role, reason]):
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
            cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            
            if not user:
                return jsonify({
                    'success': False,
                    'message': {
                        'ar': 'المستخدم غير موجود',
                        'en': 'User not found'
                    }
                }), 404
                
            current_role = user[0]
            if current_role == new_role:
                return jsonify({
                    'success': False,
                    'message': {
                        'ar': 'المستخدم لديه نفس الصلاحيات بالفعل',
                        'en': 'User already has this role'
                    }
                }), 400
            
            # إنشاء رمز تحقق جديد
            verification_code, expires_at = verification_manager.generate_verification_code(
                user_id=user_id,
                type='role_change',
                total_steps=2  # مرحلتين: تأكيد المشرف وتأكيد المشرف الثاني
            )
            
            # تسجيل طلب تغيير الصلاحيات
            cur.execute("""
                INSERT INTO role_change_history 
                (user_id, admin_id, old_role, new_role, change_reason, client_ip, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                current_user.id,
                current_role,
                new_role,
                reason,
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
            
            g.db.commit()
            
            return jsonify({
                'success': True,
                'message': {
                    'ar': 'تم إرسال طلب تغيير الصلاحيات بنجاح',
                    'en': 'Role change request sent successfully'
                },
                'verification_code': verification_code,
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
        user_id = data.get('user_id')
        verification_code = data.get('code')
        
        if not all([user_id, verification_code]):
            return jsonify({
                'success': False,
                'message': {
                    'ar': 'جميع الحقول مطلوبة',
                    'en': 'All fields are required'
                }
            }), 400
            
        # التحقق من الرمز
        verification_result = verification_manager.verify_code(
            user_id=user_id,
            code=verification_code,
            type='role_change'
        )
        
        if not verification_result['valid']:
            return jsonify({
                'success': False,
                'message': verification_result['message']
            }), 400
            
        # إذا اكتملت جميع مراحل التحقق
        if verification_result['completed']:
            cur = g.db.cursor()
            try:
                # تحديث دور المستخدم
                cur.execute("""
                    UPDATE users 
                    SET role = pending_role,
                        role_change_approved = true,
                        role_change_approver_id = %s,
                        pending_role = NULL
                    WHERE id = %s
                    RETURNING role
                """, (current_user.id, user_id))
                
                new_role = cur.fetchone()[0]
                
                # تحديث سجل التغييرات
                cur.execute("""
                    UPDATE role_change_history
                    SET approval_status = 'approved',
                        approver_id = %s,
                        approved_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    AND approval_status = 'pending'
                """, (current_user.id, user_id))
                
                g.db.commit()
                
                return jsonify({
                    'success': True,
                    'message': {
                        'ar': f'تم تحديث صلاحيات المستخدم إلى {new_role}',
                        'en': f'User role updated to {new_role}'
                    },
                    'new_role': new_role
                })
                
            finally:
                cur.close()
        
        # إذا لم تكتمل جميع المراحل
        return jsonify({
            'success': True,
            'message': verification_result['message'],
            'step': verification_result['step'],
            'total_steps': verification_result['total_steps']
        })
        
    except Exception as e:
        logger.error(f"خطأ في التحقق من تغيير الصلاحيات: {str(e)}")
        return jsonify({
            'success': False,
            'message': {
                'ar': 'حدث خطأ في معالجة الطلب',
                'en': 'Error processing request'
            }
        }), 500

@roles_bp.route('/change-status/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_change_status(user_id):
    """الحصول على حالة تغيير الصلاحيات"""
    try:
        status = verification_manager.get_verification_status(
            user_id=user_id,
            type='role_change'
        )
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"خطأ في الحصول على حالة التغيير: {str(e)}")
        return jsonify({
            'success': False,
            'message': {
                'ar': 'حدث خطأ في معالجة الطلب',
                'en': 'Error processing request'
            }
        }), 500
