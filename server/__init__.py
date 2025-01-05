"""Initialize server package"""
import os
from flask import Flask
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
import json
import firebase_admin
from firebase_admin import credentials

# Global configuration
DEFAULT_PORT = 5000  # Changed to 5000 as it's commonly available
WAIT_FOR_PORT_TIMEOUT = 30

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = WAIT_FOR_PORT_TIMEOUT) -> bool:
    """Wait for port to be available | انتظار حتى يصبح المنفذ متاحاً"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                sock.close()
                return True
        except socket.error:
            time.sleep(1)
    return False

def find_available_port(start_port: int = DEFAULT_PORT, max_attempts: int = 10) -> int:
    """Find an available port starting from the given port | البحث عن منفذ متاح بدءاً من المنفذ المحدد"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', port))
                sock.close()
                return port
        except socket.error:
            continue
    raise RuntimeError(f"No available ports found between {start_port} and {start_port + max_attempts}")

def init_firebase(logger) -> bool:
    """Initialize Firebase | تهيئة Firebase"""
    try:
        if not firebase_admin._apps:
            service_account_path = 'attached_assets/silva-deb1c-firebase-adminsdk-g19p8-5d6dc42cd6.json'

            if not os.path.exists(service_account_path):
                logger.error("Firebase service account file not found | ملف حساب الخدمة غير موجود")
                return False

            with open(service_account_path, 'r') as file:
                cred_dict = json.load(file)

            # Set environment variables from service account file
            os.environ['FIREBASE_PROJECT_ID'] = cred_dict['project_id']
            os.environ['FIREBASE_PRIVATE_KEY'] = cred_dict['private_key']
            os.environ['FIREBASE_CLIENT_EMAIL'] = cred_dict['client_email']

            # Initialize Firebase with error handling
            try:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                logger.info(f"Firebase initialized successfully for project: {cred_dict['project_id']}")
                return True
            except Exception as firebase_error:
                logger.error(f"Firebase initialization failed: {str(firebase_error)}")
                return False

        return True
    except Exception as e:
        logger.error(f"Firebase initialization error: {str(e)}")
        return False

def create_app(testing=False):
    """Create and configure Flask application | إنشاء وتكوين تطبيق Flask"""
    try:
        # Load environment variables first
        load_dotenv()

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

        # Initialize Firebase first
        if not init_firebase(logger):
            logger.error("Failed to initialize Firebase")
            return None

        # Determine environment | تحديد بيئة التشغيل
        env = os.getenv('FLASK_ENV', 'development')
        app_config = config[env]

        # Create application | إنشاء التطبيق
        app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

        # Try to find an available port
        try:
            start_port = int(os.getenv('PORT', str(DEFAULT_PORT)))
            port = find_available_port(start_port)
            logger.info(f"Found available port: {port}")
        except Exception as e:
            logger.error(f"Failed to find available port: {str(e)}")
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
        logger.info("Routes setup complete")

        # Initialize authentication after routes | تهيئة المصادقة بعد المسارات
        from server.blueprints.auth import init_auth
        app = init_auth(app)
        if app:
            logger.info("Authentication initialized successfully")
        else:
            logger.error("Failed to initialize authentication")
            return None

        logger.info(f"Application initialized successfully on port {port}")
        return app

    except Exception as e:
        if 'logger' in locals():
            logger.error(f"Error initializing application: {str(e)}")
        return None

if __name__ == '__main__':
    app = create_app()
    if app:
        port = app.config['PORT']
        app.run(host='0.0.0.0', port=port)