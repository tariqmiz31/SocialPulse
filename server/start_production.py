"""Main production server startup script"""
import os
import sys
import logging
import socket
import time
import signal
from flask import Flask, request, jsonify, session, g
from flask_cors import CORS
from flask_mail import Mail
from flask_session import Session
from flask_login import LoginManager
from datetime import timedelta
from dotenv import load_dotenv

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.database import init_db, get_db
from server.blueprints.admin import admin_bp, init_mail
from server.blueprints.auth import auth_bp
from server import logger, User

# تعريف معالج الإشارات
def signal_handler(signum, frame):
    """معالج إشارات النظام للإغلاق الآمن"""
    logger.info(f"تم استلام الإشارة {signum}. بدء الإغلاق الآمن...")
    try:
        # إغلاق الاتصالات المفتوحة
        if hasattr(g, 'db'):
            g.db.close()
        logger.info("تم إغلاق اتصالات قاعدة البيانات")
    except Exception as e:
        logger.error(f"خطأ أثناء الإغلاق: {str(e)}")
    finally:
        sys.exit(0)

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 120) -> bool:
    """انتظار توفر المنفذ"""
    start_time = time.time()
    logger.info(f"بدء انتظار المنفذ {port}...")

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                sock.close()
                logger.info(f"المنفذ {port} متاح")
                print('ready')  # إشارة الجاهزية للـ workflow
                sys.stdout.flush()
                return True
        except socket.error:
            if time.time() - start_time >= timeout:
                logger.error(f"المنفذ {port} غير متاح بعد {timeout} ثانية")
                return False
            time.sleep(1)
            logger.debug(f"انتظار المنفذ {port}...")

def init_extensions(app):
    """تهيئة امتدادات Flask بالترتيب الصحيح"""
    try:
        # 1. تهيئة Session أولاً
        flask_session = Session()
        flask_session.init_app(app)
        logger.info("تم تهيئة إدارة الجلسات")

        # 2. تهيئة نظام تسجيل الدخول
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'يجب تسجيل الدخول للوصول إلى هذه الصفحة'
        login_manager.login_message_category = 'error'

        @login_manager.user_loader
        def load_user(user_id):
            return User.get(user_id)

        logger.info("تم تهيئة نظام تسجيل الدخول")

        # 3. تهيئة خدمة البريد الإلكتروني
        flask_mail = Mail()
        flask_mail.init_app(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني")

        return flask_session, login_manager, flask_mail

    except Exception as e:
        logger.error(f"خطأ في تهيئة المكونات الأساسية: {str(e)}", exc_info=True)
        raise

def create_app(testing=False):
    """إنشاء تطبيق Flask"""
    try:
        # تحميل المتغيرات البيئية
        load_dotenv()

        # التحقق من المتغيرات البيئية المطلوبة
        required_vars = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'DATABASE_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"المتغيرات البيئية التالية مفقودة: {', '.join(missing_vars)}")
            return None

        # تسجيل معالجات الإشارات
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # إنشاء تطبيق Flask
        static_folder = os.path.abspath(os.path.join(project_root, 'client', 'dist'))
        app = Flask(__name__, static_folder=static_folder, static_url_path='/')

        # الإعدادات الأساسية
        app.config.update(
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            JSON_AS_ASCII=False,
            DEBUG=False,  # تعطيل وضع التصحيح في الإنتاج
            WAIT_FOR_PORT=True,
            WAIT_FOR_PORT_TIMEOUT=120
        )

        # إعدادات الجلسة
        app.config.update(
            SESSION_TYPE='filesystem',
            SESSION_FILE_DIR='/tmp/flask_session',
            SESSION_FILE_THRESHOLD=500,
            SESSION_PERMANENT=True,
            PERMANENT_SESSION_LIFETIME=timedelta(days=1),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax'
        )

        # إعدادات البريد الإلكتروني
        app.config.update(
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME')
        )

        # التأكد من وجود مجلد الجلسات
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])
            logger.info("تم إنشاء دليل الجلسات")

        try:
            # تهيئة المكونات الأساسية
            flask_session, login_manager, flask_mail = init_extensions(app)
        except Exception as e:
            logger.error(f"خطأ في تهيئة المكونات الأساسية: {str(e)}", exc_info=True)
            return None

        # إعداد CORS
        CORS(app, 
             supports_credentials=True,
             resources={
                 r"/api/*": {
                     "origins": ["http://localhost:5000", "https://*.repl.co", "http://0.0.0.0:5000"],
                     "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                     "allow_headers": ["Content-Type", "Authorization"],
                     "expose_headers": ["Content-Type"],
                     "supports_credentials": True
                 }
             })

        # تهيئة قاعدة البيانات
        db = init_db(app)
        if not db:
            logger.error("فشل في تهيئة قاعدة البيانات")
            return None
        logger.info("تم الاتصال بقاعدة البيانات")

        @app.before_request
        def before_request():
            """تنفيذ قبل كل طلب"""
            try:
                g.db = get_db()

                # تحديث وقت النشاط في الجلسة
                if 'user_id' in session:
                    session['last_activity'] = time.time()
                    session.modified = True
            except Exception as e:
                logger.error(f"خطأ في معالجة الطلب: {str(e)}", exc_info=True)
                return jsonify({"error": "حدث خطأ في معالجة الطلب"}), 500

        @app.teardown_appcontext
        def teardown_db(exception):
            """تنظيف موارد قاعدة البيانات"""
            db = g.pop('db', None)
            if db is not None:
                db.close()

        try:
            # تسجيل المسارات
            init_mail(flask_mail)
            app.register_blueprint(admin_bp)
            app.register_blueprint(auth_bp)
            logger.info("تم تسجيل المسارات")
        except Exception as e:
            logger.error(f"خطأ في تسجيل المسارات: {str(e)}", exc_info=True)
            return None

        @app.errorhandler(Exception)
        def handle_error(error):
            """معالجة الأخطاء العامة"""
            logger.exception("خطأ غير متوقع:")
            return jsonify({
                "error": True,
                "message": "حدث خطأ في الخادم",
                "details": str(error) if app.debug else None
            }), 500

        logger.info("تم تهيئة التطبيق بشكل كامل")
        return app

    except Exception as e:
        logger.exception("خطأ في تهيئة التطبيق:")
        return None

def main():
    """النقطة الرئيسية للدخول"""
    try:
        # تعيين وضع الإنتاج
        os.environ['FLASK_ENV'] = 'production'

        # الحصول على رقم المنفذ من متغيرات البيئة
        port = int(os.getenv('PORT', '5000'))
        logger.info(f"تهيئة الخادم على المنفذ {port}")

        # انتظار توفر المنفذ
        if not wait_for_port(port):
            logger.error(f"المنفذ {port} غير متاح")
            return 1

        # إنشاء وتهيئة التطبيق
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return 1

        # تشغيل خادم metrics
        metrics_port = port + 1
        try:
            from prometheus_client import start_http_server
            start_http_server(metrics_port)
            logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")
        except Exception as e:
            logger.warning(f"فشل في بدء خادم المقاييس: {str(e)}")

        # تشغيل الخادم باستخدام waitress
        from waitress import serve
        serve(
            app,
            host='0.0.0.0',
            port=port,
            threads=4,
            url_scheme='https'
        )

        return 0

    except Exception as e:
        logger.exception("خطأ في بدء الخادم:")
        return 1

if __name__ == "__main__":
    sys.exit(main())