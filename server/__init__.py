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
DEFAULT_PORT = 5000
WAIT_FOR_PORT_TIMEOUT = 60  # Increased timeout for production
WAIT_FOR_PORT = True  # Always wait for port

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = WAIT_FOR_PORT_TIMEOUT) -> bool:
    """Wait for port to be available"""
    if not WAIT_FOR_PORT:
        return True

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

def init_firebase(logger) -> bool:
    """Initialize Firebase"""
    try:
        if not firebase_admin._apps:
            # Use the service account file from attached_assets
            service_account_path = 'attached_assets/silva-deb1c-firebase-adminsdk-g19p8-5d6dc42cd6.json'

            if not os.path.exists(service_account_path):
                logger.error(f"Firebase service account file not found at {service_account_path}")
                return False

            try:
                with open(service_account_path, 'r') as file:
                    cred_dict = json.load(file)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing service account file: {str(e)}")
                return False
            except Exception as e:
                logger.error(f"Error reading service account file: {str(e)}")
                return False

            # Set environment variables
            os.environ['FIREBASE_PROJECT_ID'] = cred_dict['project_id']
            os.environ['FIREBASE_PRIVATE_KEY'] = cred_dict['private_key']
            os.environ['FIREBASE_CLIENT_EMAIL'] = cred_dict['client_email']

            try:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred, {
                    'auth_settings': {
                        'sms_verification_message': 'يرجى استخدام الرقم المؤقت لاستعادة كلمة المرور: %CODE%',
                        'code_length': 4
                    }
                })
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
    """Create and configure Flask application"""
    try:
        # Load environment variables first
        load_dotenv()

        # Set port waiting configuration
        os.environ['WAIT_FOR_PORT'] = 'true'

        # Initialize logger
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

        # Initialize Firebase
        try:
            if not init_firebase(logger):
                logger.error("فشل في تهيئة Firebase")
                return None

        except Exception as firebase_error:
            logger.error(f"خطأ في تهيئة Firebase: {str(firebase_error)}")
            return None

        # Determine environment
        env = os.getenv('FLASK_ENV', 'development')
        app_config = config[env]

        # Create Flask application with correct static folder path
        static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'client', 'dist'))
        app = Flask(__name__, static_folder=static_folder, static_url_path='/')

        # Configure port waiting
        port = int(os.getenv('PORT', str(DEFAULT_PORT)))
        if not wait_for_port(port):
            logger.error(f"المنفذ {port} غير متاح بعد {WAIT_FOR_PORT_TIMEOUT} ثانية")
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

        # Setup CORS
        CORS(app, supports_credentials=True)

        # Setup session
        if not testing and not os.path.exists(app_config.SESSION_FILE_DIR):
            os.makedirs(app_config.SESSION_FILE_DIR)
        Session(app)

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

        logger.info(f"تم تهيئة التطبيق بنجاح على المنفذ {port}")
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