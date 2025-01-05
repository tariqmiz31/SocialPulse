"""Initialize server package"""
import os
from flask import Flask, session
from flask_cors import CORS
from flask_session import Session
from datetime import timedelta
import logging
from logging.handlers import RotatingFileHandler
from server.routes import setup_routes
from server.config import config
from dotenv import load_dotenv
import socket
import time

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 60) -> bool:
    """Wait for port to be available | انتظار حتى يصبح المنفذ متاحاً"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.bind((host, port))
                sock.close()
                return True
        except socket.error:
            time.sleep(1)
    return False

def create_app(testing=False):
    """Create and configure Flask application | إنشاء وتكوين تطبيق Flask"""
    # Load environment variables first
    load_dotenv()

    # Verify required Firebase environment variables
    required_env_vars = ['FIREBASE_PROJECT_ID', 'FIREBASE_PRIVATE_KEY', 'FIREBASE_CLIENT_EMAIL']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Initialize logger first
    logger = logging.getLogger('silvarium')
    logger.setLevel(logging.INFO)

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

    try:
        # Determine environment | تحديد بيئة التشغيل
        env = os.getenv('FLASK_ENV', 'development')
        app_config = config[env]

        # Create application | إنشاء التطبيق
        app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

        # Configure application | تكوين التطبيق
        port = int(os.getenv('PORT', str(app_config.PORT)))

        # Wait for port availability | انتظار توفر المنفذ
        if os.getenv('WAIT_FOR_PORT', 'false').lower() == 'true':
            if not wait_for_port(port):
                logger.error(f"Port {port} is not available | المنفذ {port} غير متاح")
                return None

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
            HOST='0.0.0.0'
        )

        # Setup CORS | إعداد CORS
        CORS(app, supports_credentials=True)

        # Setup session | إعداد الجلسة
        if not testing and not os.path.exists(app_config.SESSION_FILE_DIR):
            os.makedirs(app_config.SESSION_FILE_DIR)
        Session(app)

        # Initialize routes | إعداد المسارات
        app = setup_routes(app)
        logger.info("تم إعداد المسارات | Routes setup complete")

        # Initialize authentication after routes | تهيئة المصادقة بعد المسارات
        from server.blueprints.auth import init_auth
        app = init_auth(app)
        if app:
            logger.info("تم تهيئة المصادقة بنجاح | Authentication initialized successfully")
        else:
            logger.error("فشل في تهيئة المصادقة | Failed to initialize authentication")
            return None

        logger.info("تم تهيئة التطبيق بنجاح | Application initialized successfully")
        return app

    except Exception as e:
        logger.error(f"خطأ في تهيئة التطبيق: {str(e)} | Error initializing application: {str(e)}")
        return None

if __name__ == '__main__':
    app = create_app()
    if app:
        port = app.config['PORT']
        app.run(host='0.0.0.0', port=port)