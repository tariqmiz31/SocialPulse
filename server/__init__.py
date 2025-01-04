"""Initialize server package"""
import os
from flask import Flask, session
from flask_cors import CORS
from flask_session import Session
from datetime import timedelta
import logging
from logging.handlers import RotatingFileHandler
from server.routes import setup_routes
from server.blueprints.auth import auth_bp, init_auth
from server.config import config
import socket
import time

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 60) -> bool:
    """Wait until port becomes available | انتظار حتى يصبح المنفذ متاحاً"""
    logger = logging.getLogger('silvarium')
    start_time = time.time()

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex((host, port))
                if result != 0:  # Port is available
                    logger.info(f"Port {port} is available | المنفذ {port} متاح للاستخدام")
                    return True
                if time.time() - start_time >= timeout:
                    logger.error(f"Port {port} is not available | المنفذ {port} غير متاح")
                    return False
                logger.info(f"Waiting for port {port}... | انتظار المنفذ {port}...")
                time.sleep(1)
        except Exception as e:
            logger.error(f"Error checking port {port}: {str(e)} | خطأ في فحص المنفذ {port}: {str(e)}")
            return False

def create_app(testing=False):
    """Create and configure Flask application | إنشاء وتكوين تطبيق Flask"""
    logger = None
    try:
        # Determine environment | تحديد بيئة التشغيل
        env = os.getenv('FLASK_ENV', 'development')
        app_config = config[env]

        # Setup logging | إعداد التسجيل
        if not testing:
            logger = logging.getLogger('silvarium')
            logger.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

            if not os.path.exists('/tmp/logs'):
                os.makedirs('/tmp/logs')

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

        # Create application | إنشاء التطبيق
        app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

        # Configure application | تكوين التطبيق
        app.config.update(
            SESSION_TYPE=app_config.SESSION_TYPE,
            SESSION_FILE_DIR=app_config.SESSION_FILE_DIR,
            SESSION_COOKIE_SECURE=app_config.SESSION_COOKIE_SECURE,
            SESSION_COOKIE_HTTPONLY=app_config.SESSION_COOKIE_HTTPONLY,
            SESSION_COOKIE_SAMESITE=app_config.SESSION_COOKIE_SAMESITE,
            PERMANENT_SESSION_LIFETIME=timedelta(seconds=app_config.PERMANENT_SESSION_LIFETIME),
            SECRET_KEY=app_config.SECRET_KEY,
            DEBUG=app_config.DEBUG,
            PORT=int(os.getenv('PORT', str(app_config.PORT))),
            HOST='0.0.0.0',
            TESTING=testing
        )

        # Set default language | تعيين اللغة الافتراضية
        @app.before_request
        def set_default_language():
            if 'language' not in session:
                session['language'] = app_config.DEFAULT_LANGUAGE

        # Setup CORS | إعداد CORS
        CORS(app, 
             supports_credentials=True,
             resources={
                 r"/api/*": {
                     "origins": app_config.CORS_ORIGINS,
                     "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                     "allow_headers": ["Content-Type", "Authorization"],
                     "expose_headers": ["Content-Range", "X-Content-Range"],
                     "supports_credentials": True
                 }
             })

        # Wait for port if not testing | انتظار المنفذ إذا لم يكن في وضع الاختبار
        if not testing and app_config.WAIT_FOR_PORT:
            port = app.config['PORT']
            if not wait_for_port(port, app.config['HOST'], app_config.WAIT_FOR_PORT_TIMEOUT):
                if logger:
                    logger.error(f"Port {port} is not available | المنفذ {port} غير متاح")
                return None

        # Setup authentication | إعداد المصادقة
        app = init_auth(app)

        # Create session directory | إنشاء مجلد الجلسات
        if not testing and not os.path.exists(app_config.SESSION_FILE_DIR):
            os.makedirs(app_config.SESSION_FILE_DIR)

        # Setup session | إعداد الجلسة
        Session(app)

        # Setup routes | إعداد المسارات
        app = setup_routes(app)

        # Log successful initialization | تسجيل نجاح التهيئة
        if logger:
            logger.info('Application initialized successfully | تم تهيئة التطبيق بنجاح')
            logger.info(f'Application configured to run on {app.config["HOST"]}:{app.config["PORT"]} | التطبيق مكون للعمل على {app.config["HOST"]}:{app.config["PORT"]}')

        return app

    except Exception as e:
        if logger:
            logger.error(f'Application initialization error: {str(e)} | خطأ في تهيئة التطبيق: {str(e)}')
        return None

if __name__ == '__main__':
    app = create_app()
    if app:
        port = app.config['PORT']
        app.run(host='0.0.0.0', port=port)