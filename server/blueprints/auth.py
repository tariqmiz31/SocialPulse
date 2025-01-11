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
            return jsonify({'message': 'البيانات المطلوبة غير موجودة'}), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            logger.warning("محاولة تسجيل دخول مع بيانات ناقصة")
            return jsonify({'message': 'اسم المستخدم وكلمة المرور مطلوبة'}), 400

        db = get_db()
        if not db:
            logger.error("فشل في الاتصال بقاعدة البيانات")
            return jsonify({'message': 'خطأ في الاتصال بقاعدة البيانات'}), 500

        cursor = db.cursor()

        try:
            # Check login attempts
            cursor.execute("""
                SELECT COUNT(*) 
                FROM verification_attempts 
                WHERE email = %s 
                AND attempt_time > NOW() - INTERVAL '1 hour'
            """, (username,))

            attempt_count = cursor.fetchone()[0]
            if attempt_count >= 5:
                logger.warning(f"تجاوز عدد محاولات تسجيل الدخول للمستخدم {username}")
                return jsonify({'message': 'تم تجاوز الحد الأقصى لمحاولات تسجيل الدخول. الرجاء المحاولة لاحقاً'}), 429

            cursor.execute("""
                SELECT id, username, email, role, status, password
                FROM users
                WHERE username = %s AND status = 'active'
            """, (username,))

            user_data = cursor.fetchone()

            if user_data and check_password_hash(user_data[5], password):
                user = User(user_data)
                login_user(user)

                # Update session with secure settings
                session['user_id'] = user.id
                session['last_activity'] = time.time()
                session.permanent = True
                session.modified = True

                logger.info(f"تم تسجيل دخول المستخدم {username} بنجاح")

                return jsonify({
                    'message': 'تم تسجيل الدخول بنجاح',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'role': user.role
                    }
                }), 200

            # Record failed attempt
            cursor.execute("""
                INSERT INTO verification_attempts (email, attempt_time)
                VALUES (%s, NOW())
            """, (username,))
            db.commit()

            logger.warning(f"محاولة تسجيل دخول فاشلة للمستخدم {username}")
            return jsonify({'message': 'اسم المستخدم أو كلمة المرور غير صحيحة'}), 401

        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"خطأ في تسجيل الدخول: {str(e)}", exc_info=True)
        return jsonify({'message': 'حدث خطأ أثناء تسجيل الدخول'}), 500

@auth_bp.route('/api/logout', methods=['POST', 'OPTIONS'])
@login_required
def logout():
    """تسجيل الخروج"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        username = current_user.username
        logout_user()

        # Clear session safely
        session.clear()
        session.modified = True

        logger.info(f"تم تسجيل خروج المستخدم {username} بنجاح")
        return jsonify({'message': 'تم تسجيل الخروج بنجاح'})
    except Exception as e:
        logger.error(f"خطأ في تسجيل الخروج: {str(e)}", exc_info=True)
        return jsonify({'message': 'حدث خطأ أثناء تسجيل الخروج'}), 500

@auth_bp.route('/api/user/current', methods=['GET', 'OPTIONS'])
def get_current_user():
    """الحصول على معلومات المستخدم الحالي"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        if current_user.is_authenticated:
            logger.debug(f"تم طلب معلومات المستخدم الحالي: {current_user.username}")
            return jsonify({
                'id': current_user.id,
                'username': current_user.username,
                'role': current_user.role,
                'status': current_user.status
            })
        logger.debug("محاولة الوصول لمعلومات المستخدم بدون تسجيل دخول")
        return jsonify({'message': 'المستخدم غير مسجل الدخول'}), 401
    except Exception as e:
        logger.error(f"خطأ في جلب معلومات المستخدم الحالي: {str(e)}", exc_info=True)
        return jsonify({'message': 'حدث خطأ في جلب معلومات المستخدم'}), 500

@auth_bp.before_request
def check_session():
    """التحقق من صلاحية الجلسة"""
    try:
        if 'user_id' in session and 'last_activity' in session:
            # Check session expiry
            session_timeout = current_app.config.get('PERMANENT_SESSION_LIFETIME', 24 * 60 * 60)  # Default 24 hours
            if time.time() - session['last_activity'] > session_timeout:
                logger.info("انتهت صلاحية الجلسة")
                session.clear()
                return jsonify({'message': 'انتهت صلاحية الجلسة'}), 401
            session['last_activity'] = time.time()
            session.modified = True
    except Exception as e:
        logger.error(f"خطأ في التحقق من صلاحية الجلسة: {str(e)}", exc_info=True)