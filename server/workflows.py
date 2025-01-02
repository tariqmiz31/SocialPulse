from flask import Flask
from flask_cors import CORS
from flask_session import Session
from waitress import serve
import logging
from logging.handlers import RotatingFileHandler
import socket
import os
import time
from server.auth import setup_auth
from server.routes import setup_routes

def setup_workflow_logging():
    """إعداد التسجيل للتدفق العملي"""
    logger = logging.getLogger('silvarium_workflow')
    logger.setLevel(logging.INFO)

    log_dir = '/tmp/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    handler = RotatingFileHandler(
        f'{log_dir}/silvarium_workflow.log',
        maxBytes=1024 * 1024,  # 1MB
        backupCount=3
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    logger.addHandler(handler)
    return logger

def is_port_in_use(port: int) -> bool:
    """التحقق مما إذا كان المنفذ قيد الاستخدام"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error as e:
            logging.error(f"خطأ في فحص المنفذ {port}: {str(e)}")
            return True

def wait_for_port(port: int, logger, timeout=60):
    """انتظار حتى يصبح المنفذ متاحًا"""
    logger.info(f"بدء انتظار المنفذ {port}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            logger.info(f"المنفذ {port} متاح الآن")
            return True
        logger.debug(f"المنفذ {port} مشغول، انتظار...")
        time.sleep(1)

    logger.error(f"انتهت مهلة انتظار المنفذ {port}")
    return False

def create_app():
    """إنشاء وإعداد تطبيق Flask"""
    app = Flask(__name__, static_folder='../client/dist', static_url_path='/')
    app.config['PROPAGATE_EXCEPTIONS'] = True

    # تكوين CORS
    CORS(app, 
         supports_credentials=True, 
         resources={
             r"/api/*": {
                 "origins": ["https://*.repl.co", "https://*.repl.dev"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "expose_headers": ["Content-Range", "X-Content-Range"],
                 "supports_credentials": True
             }
         })

    # تكوين الجلسة
    app.config.update(
        SESSION_TYPE='filesystem',
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes
        SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex())
    )
    Session(app)

    # إعداد المصادقة والمسارات
    app = setup_auth(app)
    app = setup_routes(app)

    return app

def start_server():
    """بدء تشغيل الخادم مع التعامل مع الأخطاء وإدارة المنافذ"""
    logger = setup_workflow_logging()
    try:
        logger.info("بدء تشغيل خادم Silvarium Social...")

        # تحديد المنفذ
        port = int(os.getenv("PORT", "5001"))

        # انتظار حتى يصبح المنفذ متاحًا
        if not wait_for_port(port, logger, timeout=120):  # زيادة مهلة الانتظار إلى دقيقتين
            logger.error(f"فشل في انتظار المنفذ {port}")
            return False

        # إنشاء وتكوين التطبيق
        app = create_app()
        logger.info("تم إنشاء التطبيق بنجاح")

        # بدء التشغيل
        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")
        serve(
            app,
            host="0.0.0.0",
            port=port,
            url_scheme='https',
            threads=4,
            connection_limit=1000,
            channel_timeout=30,
            _quiet=False  # تمكين سجلات Waitress
        )

        return True

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        raise

if __name__ == "__main__":
    start_server()