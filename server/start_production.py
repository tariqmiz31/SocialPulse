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

def signal_handler(signum, frame):
    """معالج إشارات النظام"""
    logger.info(f"تم استلام الإشارة {signum}. إغلاق التطبيق...")
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
                return True
        except socket.error:
            if time.time() - start_time >= timeout:
                logger.error(f"المنفذ {port} غير متاح بعد {timeout} ثانية")
                return False
            time.sleep(1)
            logger.info(f"انتظار المنفذ {port}...")

def create_app(testing=False):
    """إنشاء تطبيق Flask"""
    try:
        # Load environment variables
        load_dotenv()

        # Check required environment variables
        required_vars = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'DATABASE_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"المتغيرات البيئية التالية مفقودة: {', '.join(missing_vars)}")
            return None

        # Create Flask app
        static_folder = os.path.abspath(os.path.join(project_root, 'client', 'dist'))
        app = Flask(__name__, static_folder=static_folder, static_url_path='/')

        # Basic app configuration
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
        app.config['JSON_AS_ASCII'] = False
        app.config['DEBUG'] = False  # Ensure debug is off in production

        # Session configuration
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

        # Email configuration
        app.config.update(
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME')
        )

        # Ensure session directory exists
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])
            logger.info("تم إنشاء دليل الجلسات")

        # Initialize core extensions
        session_interface = Session()
        session_interface.init_app(app)
        logger.info("تم تهيئة إدارة الجلسات")

        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'يجب تسجيل الدخول للوصول إلى هذه الصفحة'
        login_manager.login_message_category = 'error'

        @login_manager.user_loader
        def load_user(user_id):
            return User.get(user_id)

        logger.info("تم تهيئة نظام تسجيل الدخول")

        mail = Mail()
        mail.init_app(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني")

        # Configure CORS
        CORS(app, 
             supports_credentials=True,
             resources={
                 r"/api/*": {
                     "origins": ["https://*.repl.co", "https://*.repl.dev"],
                     "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                     "allow_headers": ["Content-Type", "Authorization"],
                     "expose_headers": ["Content-Type"],
                     "supports_credentials": True
                 }
             })

        # Initialize database
        db = init_db(app)
        if not db:
            logger.error("فشل في تهيئة قاعدة البيانات")
            return None
        logger.info("تم الاتصال بقاعدة البيانات")

        @app.before_request
        def before_request():
            """تنفيذ قبل كل طلب"""
            try:
                # تحديث وقت النشاط للجلسة
                if 'user_id' in session:
                    session['last_activity'] = time.time()
                    session.modified = True

                # تهيئة اتصال قاعدة البيانات
                g.db = get_db()

            except Exception as e:
                logger.exception("خطأ في معالجة الطلب:")
                return jsonify({"error": "حدث خطأ في معالجة الطلب"}), 500

        @app.teardown_appcontext
        def teardown_db(exception):
            """تنظيف موارد قاعدة البيانات"""
            db = g.pop('db', None)
            if db is not None:
                db.close()

        # Register blueprints
        init_mail(mail)
        app.register_blueprint(admin_bp)
        app.register_blueprint(auth_bp)
        logger.info("تم تسجيل المسارات")

        @app.errorhandler(Exception)
        def handle_error(error):
            """معالجة الأخطاء العامة"""
            logger.exception("خطأ غير متوقع:")
            return jsonify({
                "error": True,
                "message": "حدث خطأ في الخادم",
                "details": str(error) if app.debug else None
            }), 500

        logger.info("تم تهيئة التطبيق بنجاح")
        return app

    except Exception as e:
        logger.exception("خطأ في تهيئة التطبيق:")
        return None

def main():
    """النقطة الرئيسية للدخول"""
    try:
        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Set production mode
        os.environ['FLASK_ENV'] = 'production'

        # Get port from environment
        port = int(os.getenv('PORT', '5000'))
        logger.info(f"تهيئة الخادم على المنفذ {port}")

        # Wait for port availability
        if not wait_for_port(port):
            logger.error(f"المنفذ {port} غير متاح")
            return 1

        # Create and configure app
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return 1

        # Start metrics server
        metrics_port = port + 1
        try:
            from prometheus_client import start_http_server
            start_http_server(metrics_port)
            logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")
        except Exception as e:
            logger.warning(f"فشل في بدء خادم المقاييس: {str(e)}")

        # Signal ready for workflow
        print('ready')
        sys.stdout.flush()
        logger.info("جميع الأنظمة جاهزة للعمل")

        # Start production server with waitress
        from waitress import serve
        serve(
            app,
            host='0.0.0.0',
            port=port,
            threads=4,
            url_scheme='https',
            channel_timeout=30,
            cleanup_interval=30,
            ident='Silvarium Social'
        )

        return 0

    except Exception as e:
        logger.exception("خطأ في بدء الخادم:")
        return 1

if __name__ == "__main__":
    sys.exit(main())