"""Initialize server package"""
import os
from flask import Flask
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

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 60):
    """انتظار حتى يصبح المنفذ متاحاً | Wait until port becomes available"""
    logger = logging.getLogger('silvarium')
    start_time = time.time()

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Try to connect to check if port is in use
                result = sock.connect_ex((host, port))
                if result != 0:  # Port is available
                    logger.info(f"المنفذ {port} متاح للاستخدام | Port {port} is available")
                    return True
                else:  # Port is in use
                    if time.time() - start_time >= timeout:
                        logger.error(f"المنفذ {port} غير متاح | Port {port} is not available")
                        return False
                    logger.info(f"انتظار المنفذ {port}... | Waiting for port {port}...")
                    time.sleep(1)
        except Exception as e:
            logger.error(f"خطأ في فحص المنفذ {port}: {str(e)} | Error checking port {port}: {str(e)}")
            if time.time() - start_time >= timeout:
                return False
            time.sleep(1)

def setup_logging(app_config):
    """إعداد التسجيل | Setup logging"""
    logger = logging.getLogger('silvarium')
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')

    log_dir = '/tmp/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    file_handler = RotatingFileHandler(
        f'{log_dir}/silvarium.log',
        maxBytes=1024 * 1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

def create_app():
    """إنشاء وتكوين تطبيق Flask"""
    # تحديد بيئة التشغيل | Determine environment
    env = os.getenv('FLASK_ENV', 'development')  # Default to development
    app_config = config[env]

    # إعداد التسجيل | Setup logging
    logger = setup_logging(app_config)

    # إنشاء التطبيق | Create application
    app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

    # تكوين التطبيق | Configure application
    app.config.update(
        SESSION_TYPE=app_config.SESSION_TYPE,
        SESSION_FILE_DIR=app_config.SESSION_FILE_DIR,
        SESSION_COOKIE_SECURE=app_config.SESSION_COOKIE_SECURE,
        SESSION_COOKIE_HTTPONLY=app_config.SESSION_COOKIE_HTTPONLY,
        SESSION_COOKIE_SAMESITE=app_config.SESSION_COOKIE_SAMESITE,
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=app_config.PERMANENT_SESSION_LIFETIME),
        SECRET_KEY=app_config.SECRET_KEY,
        DEBUG=app_config.DEBUG,
        PORT=app_config.PORT,
        HOST=app_config.HOST,
        WAIT_FOR_PORT=True,  # Always wait for port
        WAIT_FOR_PORT_TIMEOUT=60  # 60 seconds timeout
    )

    # إعداد CORS | Setup CORS
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

    # انتظار المنفذ | Wait for port
    port = app.config['PORT']
    if not wait_for_port(port, app.config['HOST'], app.config['WAIT_FOR_PORT_TIMEOUT']):
        logger.error(f"المنفذ {port} غير متاح | Port {port} is not available")
        return None

    # إعداد المصادقة | Setup authentication
    app = init_auth(app)

    # إنشاء مجلد الجلسات | Create session directory
    session_dir = app_config.SESSION_FILE_DIR
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)

    # إعداد الجلسة | Setup session
    Session(app)

    # إعداد المسارات | Setup routes
    app = setup_routes(app)

    # تسجيل نجاح التهيئة | Log successful initialization
    logger.info('تم تهيئة التطبيق بنجاح | Application initialized successfully')
    logger.info(f'التطبيق مكون للعمل على {app.config["HOST"]}:{app.config["PORT"]} | Application configured to run on {app.config["HOST"]}:{app.config["PORT"]}')

    return app

if __name__ == '__main__':
    app = create_app()
    if app:
        port = int(os.getenv('PORT', '8080'))
        app.run(host='0.0.0.0', port=port)