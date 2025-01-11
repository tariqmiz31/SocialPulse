"""Main production server startup script"""
import os
import sys
import logging
from waitress import serve
from prometheus_client import start_http_server
import socket
import time
import signal
from flask import Flask, request, jsonify, session, g
from flask_cors import CORS
from flask_mail import Mail
from flask_session import Session
from flask_login import LoginManager
from datetime import timedelta
import psycopg2
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

# Initialize Flask extensions
mail = Mail()
sess = Session()
login_manager = LoginManager()

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
        logger.info("تم تحميل المتغيرات البيئية")

        # Check required environment variables
        required_vars = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'DATABASE_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"المتغيرات البيئية التالية مفقودة: {', '.join(missing_vars)}")
            return None

        # Create Flask app
        static_folder = os.path.abspath(os.path.join(project_root, 'client', 'dist'))
        app = Flask(__name__, static_folder=static_folder, static_url_path='/')
        logger.info("تم إنشاء تطبيق Flask")

        # Configure app
        app.config.update(
            DEBUG=False,
            TESTING=testing,
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME'),
            SESSION_TYPE='filesystem',
            SESSION_PERMANENT=True,
            PERMANENT_SESSION_LIFETIME=timedelta(days=1),
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            SESSION_FILE_DIR='/tmp/flask_session',
            SESSION_FILE_THRESHOLD=500,
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            JSON_AS_ASCII=False,
            WAIT_FOR_PORT=True,
            WAIT_FOR_PORT_TIMEOUT=120
        )
        logger.info("تم تكوين إعدادات التطبيق")

        # Setup Session directory
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])
            logger.info("تم إنشاء دليل الجلسات")

        # Initialize Flask extensions in the correct order
        mail.init_app(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني")

        sess.init_app(app)
        logger.info("تم تهيئة إدارة الجلسات")

        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        logger.info("تم تهيئة نظام تسجيل الدخول")

        @login_manager.user_loader
        def load_user(user_id):
            """تحميل المستخدم من قاعدة البيانات"""
            return User.get(user_id)

        # Setup CORS with proper configuration
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
        logger.info("تم تكوين CORS")

        # Initialize database
        db = init_db(app)
        if not db:
            logger.error("فشل في تهيئة قاعدة البيانات")
            return None
        logger.info("تم الاتصال بقاعدة البيانات")

        @app.before_request
        def before_request():
            """تنفيذ قبل كل طلب"""
            # تهيئة اتصال قاعدة البيانات
            g.db = get_db()

            # التحقق من صلاحية الجلسة للمسارات المحمية
            if request.path.startswith('/api/'):
                if not request.path.startswith('/api/login') and \
                   not request.path.startswith('/api/register'):
                    if 'user_id' not in session:
                        logger.warning("محاولة وصول بدون تسجيل دخول")
                        return jsonify({"message": "يجب تسجيل الدخول"}), 401

                    if 'last_activity' in session:
                        if time.time() - session['last_activity'] > app.config['PERMANENT_SESSION_LIFETIME'].total_seconds():
                            session.clear()
                            logger.warning("تم تسجيل الخروج تلقائياً بسبب انتهاء صلاحية الجلسة")
                            return jsonify({"message": "انتهت صلاحية الجلسة"}), 401

                        session['last_activity'] = time.time()
                        session.modified = True

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
            logger.error(f"خطأ غير متوقع: {str(error)}")
            return jsonify({
                "error": True,
                "message": "حدث خطأ في الخادم",
                "details": str(error) if app.debug else None
            }), 500

        # Signal ready for workflow
        print('ready')
        sys.stdout.flush()
        logger.info("تم تهيئة التطبيق بنجاح وهو جاهز للاستخدام")

        return app

    except Exception as e:
        logger.error(f"خطأ في تهيئة التطبيق: {str(e)}")
        return None

def main():
    """النقطة الرئيسية للدخول"""
    try:
        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Set production mode
        os.environ['FLASK_ENV'] = 'production'
        os.environ['SERVER_SOFTWARE'] = 'Waitress'

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
            start_http_server(metrics_port)
            logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")
        except Exception as e:
            logger.warning(f"فشل في بدء خادم المقاييس: {str(e)}")

        logger.info("جميع الأنظمة جاهزة للعمل")

        # Start production server with waitress
        serve(
            app,
            host='0.0.0.0',
            port=port,
            threads=4,
            url_scheme='https',
            channel_timeout=30,
            cleanup_interval=30,
            ident='Silvarium Social',
            clear_untrusted_proxy_headers=True,
            trusted_proxy_headers=['x-forwarded-for', 'x-forwarded-proto'],
            trusted_proxy='127.0.0.1'
        )

        return 0

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())