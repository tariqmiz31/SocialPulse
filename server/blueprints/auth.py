from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from server.database import get_db
from server import logger, User
import time

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    """تسجيل الدخول"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        if current_user.is_authenticated:
            logger.info(f"محاولة تسجيل دخول لمستخدم مسجل بالفعل: {current_user.username}")
            return jsonify({
                'status': 'success',
                'message': 'أنت مسجل الدخول بالفعل',
                'user': {
                    'id': current_user.id,
                    'username': current_user.username,
                    'role': current_user.role
                }
            }), 200

        data = request.get_json()
        if not data:
            logger.warning("محاولة تسجيل دخول بدون بيانات")
            return jsonify({
                'status': 'error',
                'message': 'البيانات المطلوبة غير موجودة',
                'code': 'missing_data'
            }), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            logger.warning("محاولة تسجيل دخول مع بيانات ناقصة")
            return jsonify({
                'status': 'error',
                'message': 'اسم المستخدم وكلمة المرور مطلوبة',
                'code': 'incomplete_data'
            }), 400

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
            # التحقق من عدد محاولات تسجيل الدخول
            cursor.execute("""
                SELECT COUNT(*) 
                FROM verification_attempts 
                WHERE email = %s 
                AND attempt_time > NOW() - INTERVAL '1 hour'
            """, (username,))

            attempt_count = cursor.fetchone()[0]
            if attempt_count >= 5:
                logger.warning(f"تجاوز عدد محاولات تسجيل الدخول للمستخدم {username}")
                return jsonify({
                    'status': 'error',
                    'message': 'تم تجاوز الحد الأقصى لمحاولات تسجيل الدخول. الرجاء المحاولة لاحقاً',
                    'code': 'too_many_attempts'
                }), 429

            cursor.execute("""
                SELECT id, username, email, role, status, password
                FROM users
                WHERE username = %s AND status = 'active'
            """, (username,))

            user_data = cursor.fetchone()

            if user_data and check_password_hash(user_data[5], password):
                user = User(user_data)
                login_user(user)

                # تحديث معلومات الجلسة
                session['user_id'] = user.id
                session['last_activity'] = time.time()
                session.permanent = True
                session.modified = True

                logger.info(f"تم تسجيل دخول المستخدم {username} بنجاح")

                return jsonify({
                    'status': 'success',
                    'message': 'تم تسجيل الدخول بنجاح',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'role': user.role
                    }
                }), 200

            # تسجيل محاولة فاشلة
            cursor.execute("""
                INSERT INTO verification_attempts (email, attempt_time)
                VALUES (%s, NOW())
            """, (username,))
            db.commit()

            logger.warning(f"محاولة تسجيل دخول فاشلة للمستخدم {username}")
            return jsonify({
                'status': 'error',
                'message': 'اسم المستخدم أو كلمة المرور غير صحيحة',
                'code': 'invalid_credentials'
            }), 401

        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"خطأ في تسجيل الدخول: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ أثناء تسجيل الدخول',
            'code': 'internal_error'
        }), 500

@auth_bp.route('/api/logout', methods=['POST', 'OPTIONS'])
@login_required
def logout():
    """تسجيل الخروج"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        username = current_user.username
        logout_user()

        # تنظيف الجلسة بشكل آمن
        session.clear()
        session.modified = True

        logger.info(f"تم تسجيل خروج المستخدم {username} بنجاح")
        return jsonify({
            'status': 'success',
            'message': 'تم تسجيل الخروج بنجاح'
        })
    except Exception as e:
        logger.error(f"خطأ في تسجيل الخروج: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ أثناء تسجيل الخروج',
            'code': 'internal_error'
        }), 500

@auth_bp.route('/api/user/current', methods=['GET', 'OPTIONS'])
def get_current_user():
    """الحصول على معلومات المستخدم الحالي"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        if current_user.is_authenticated:
            logger.debug(f"تم طلب معلومات المستخدم الحالي: {current_user.username}")
            return jsonify({
                'status': 'success',
                'user': {
                    'id': current_user.id,
                    'username': current_user.username,
                    'role': current_user.role,
                    'status': current_user.status
                }
            })
        logger.debug("محاولة الوصول لمعلومات المستخدم بدون تسجيل دخول")
        return jsonify({
            'status': 'error',
            'message': 'المستخدم غير مسجل الدخول',
            'code': 'unauthorized'
        }), 401
    except Exception as e:
        logger.error(f"خطأ في جلب معلومات المستخدم الحالي: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ في جلب معلومات المستخدم',
            'code': 'internal_error'
        }), 500

@auth_bp.before_request
def check_session():
    """التحقق من صلاحية الجلسة"""
    try:
        if 'user_id' in session and 'last_activity' in session:
            # التحقق من انتهاء صلاحية الجلسة
            session_timeout = current_app.config.get('PERMANENT_SESSION_LIFETIME', 24 * 60 * 60)  # الافتراضي 24 ساعة
            if time.time() - session['last_activity'] > session_timeout:
                logger.info("انتهت صلاحية الجلسة")
                session.clear()
                return jsonify({
                    'status': 'error',
                    'message': 'انتهت صلاحية الجلسة',
                    'code': 'session_expired'
                }), 401
            session['last_activity'] = time.time()
            session.modified = True
    except Exception as e:
        logger.error(f"خطأ في التحقق من صلاحية الجلسة: {str(e)}", exc_info=True)