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

# Setup logging
logger = logging.getLogger('silvarium')
logger.setLevel(logging.INFO)

def create_app(testing=False):
    """Create and configure Flask application"""
    try:
        # Load environment variables first
        load_dotenv()

        # Set port waiting configuration
        os.environ['WAIT_FOR_PORT'] = 'true'

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
            from server.blueprints.auth import init_verification_tables
            if not init_verification_tables():
                logger.error("فشل في تهيئة جداول التحقق")
                return None
            logger.info("تم تهيئة جداول التحقق بنجاح")

        except Exception as firebase_error:
            logger.error(f"خطأ في تهيئة النظام: {str(firebase_error)}")
            return None

        # Determine environment
        env = os.getenv('FLASK_ENV', 'development')
        app_config = config[env]

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
            PORT=int(os.getenv('PORT', '5000')),
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