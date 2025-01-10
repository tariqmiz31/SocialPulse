"""Initialize server package"""
import os
from flask import Flask
from flask_cors import CORS
from flask_session import Session
from datetime import timedelta
import logging
import socket
import time
from logging.handlers import RotatingFileHandler
from server.routes import setup_routes
from server.config import config
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger('silvarium')
logger.setLevel(logging.INFO)

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 120) -> bool:
    """Wait for port availability"""
    logger.info(f"بدء انتظار المنفذ {port}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                sock.close()
                logger.info(f"المنفذ {port} متاح")
                return True
        except socket.error:
            time.sleep(1)
            logger.info(f"انتظار المنفذ {port}...")

    logger.error(f"المنفذ {port} غير متاح بعد {timeout} ثانية")
    return False

def create_app(testing=False):
    """Create and configure Flask application"""
    try:
        # Load environment variables first
        load_dotenv()

        if not testing:
            # Setup logging handlers
            if not os.path.exists('/tmp/logs'):
                os.makedirs('/tmp/logs')

            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

            file_handler = RotatingFileHandler(
                '/tmp/logs/silvarium.log',
                maxBytes=1024 * 1024,
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # Initialize authentication and email service
        try:
            # Import and initialize email service first
            from server.blueprints.auth.email_service import email_service
            from server.blueprints.auth import init_verification_tables

            if not init_verification_tables():
                logger.error("فشل في تهيئة جداول التحقق")
                return None
            logger.info("تم تهيئة جداول التحقق بنجاح")

        except Exception as e:
            logger.error(f"خطأ في تهيئة النظام: {str(e)}")
            return None

        # Determine environment
        env = os.getenv('FLASK_ENV', 'development')
        app_config = config[env]

        # Get port from environment or config
        port = int(os.getenv('PORT', '5000'))

        # Wait for port if configured
        if app_config.WAIT_FOR_PORT and not testing:
            if not wait_for_port(port, timeout=app_config.WAIT_FOR_PORT_TIMEOUT):
                logger.error("فشل في انتظار المنفذ")
                return None
            logger.info("تم تأكيد توفر المنفذ بنجاح")

        # Create Flask application with correct static folder path
        static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'client', 'dist'))
        app = Flask(__name__, static_folder=static_folder, static_url_path='/')

        app.config.update(
            SESSION_TYPE=app_config.SESSION_TYPE,
            SESSION_FILE_DIR=app_config.SESSION_FILE_DIR,
            SESSION_COOKIE_SECURE=app_config.SESSION_COOKIE_SECURE,
            SESSION_COOKIE_HTTPONLY=app_config.SESSION_COOKIE_HTTPONLY,
            SESSION_COOKIE_SAMESITE=app_config.SESSION_COOKIE_SAMESITE,
            PERMANENT_SESSION_LIFETIME=timedelta(seconds=app_config.PERMANENT_SESSION_LIFETIME),
            SECRET_KEY=app_config.SECRET_KEY,
            DEBUG=app_config.DEBUG,
            PORT=port,
            HOST='0.0.0.0',
            WAIT_FOR_PORT=app_config.WAIT_FOR_PORT,
            WAIT_FOR_PORT_TIMEOUT=app_config.WAIT_FOR_PORT_TIMEOUT
        )

        # Setup CORS
        CORS(app, supports_credentials=True)

        # Setup session
        if not testing and not os.path.exists(app_config.SESSION_FILE_DIR):
            os.makedirs(app_config.SESSION_FILE_DIR)
        Session(app)

        # Initialize email service
        email_service.init_mail(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني بنجاح")

        # Initialize routes
        app = setup_routes(app)
        logger.info("تم إعداد المسارات بنجاح")

        # Initialize authentication
        from server.blueprints.auth import init_auth
        app = init_auth(app)
        if app:
            logger.info("تم تهيئة المصادقة بنجاح")
        else:
            logger.error("فشل في تهيئة المصادقة")
            return None

        logger.info(f"تم تهيئة التطبيق بنجاح على المنفذ {app.config['PORT']}")
        return app

    except Exception as e:
        if 'logger' in locals():
            logger.error(f"خطأ في تهيئة التطبيق: {str(e)}")
        return None

if __name__ == '__main__':
    app = create_app()
    if app:
        port = app.config['PORT']
        app.run(host='0.0.0.0', port=port)