"""Main production server startup script"""
import os
import sys
import logging
from waitress import serve
from prometheus_client import start_http_server
import socket
import time
from flask import Flask
from flask_cors import CORS
from flask_mail import Mail
from flask_session import Session
from dotenv import load_dotenv
from datetime import timedelta
import psycopg2
from flask_login import LoginManager

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import local modules after path setup
from server.database import init_db
from server.blueprints.admin import admin_bp, init_mail
from server.blueprints.auth import auth_bp
from server import logger, User

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 120) -> bool:
    """Wait for port availability"""
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
    """Create Flask application"""
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

        # Setup Session directory
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])

        # Initialize Flask extensions in the correct order
        mail = Mail(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني بنجاح")

        session = Session(app)
        logger.info("تم تهيئة إدارة الجلسات بنجاح")

        login_manager = LoginManager(app)
        login_manager.login_view = 'auth.login'
        logger.info("تم تهيئة نظام تسجيل الدخول بنجاح")

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

        # Initialize database
        db = init_db(app)
        if not db:
            logger.error("فشل في تهيئة قاعدة البيانات")
            return None
        logger.info("تم الاتصال بقاعدة البيانات بنجاح")

        @login_manager.user_loader
        def load_user(user_id):
            return User.get(user_id)

        # Register blueprints after all initializations
        init_mail(mail)  # Initialize mail for admin blueprint
        app.register_blueprint(admin_bp)
        app.register_blueprint(auth_bp)
        logger.info("تم تسجيل المسارات بنجاح")

        return app

    except Exception as e:
        logger.error(f"خطأ في تهيئة التطبيق: {str(e)}")
        return None

def main():
    """Main entry point"""
    try:
        # Set production mode
        os.environ['FLASK_ENV'] = 'production'
        os.environ['SERVER_SOFTWARE'] = 'Waitress'

        # Use port from environment
        port = int(os.getenv('PORT', '5000'))

        # Wait for port availability
        if not wait_for_port(port):
            logger.error(f"المنفذ {port} غير متاح بعد {120} ثانية")
            return 1

        # Create Flask app
        logger.info("إنشاء تطبيق Flask")
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return 1

        # Start metrics server on a different port
        metrics_port = port + 1
        try:
            start_http_server(metrics_port)
            logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")
        except Exception as e:
            logger.warning(f"فشل في بدء خادم المقاييس: {str(e)}")

        # Signal ready for workflow before starting the server
        print('ready')
        sys.stdout.flush()

        # Start production server with waitress
        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")
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