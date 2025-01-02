import os
import sys
from waitress import serve
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import prometheus_client
from prometheus_client import Counter, Histogram
from flask import Flask, send_from_directory, request
from flask_cors import CORS
from flask_session import Session
import psycopg2
import time
import socket
import signal

# إضافة المسار الرئيسي إلى PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.auth import setup_auth
from server.routes import setup_routes

def setup_logging():
    """إعداد التسجيل"""
    logger = logging.getLogger('silvarium_production')
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    # إعداد تسجيل الملف
    log_dir = '/tmp/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    file_handler = RotatingFileHandler(
        f'{log_dir}/silvarium_production.log',
        maxBytes=1024 * 1024,  # 1MB
        backupCount=3
    )
    file_handler.setFormatter(formatter)

    # إعداد تسجيل وحدة التحكم
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def wait_for_port(port: int, logger, timeout=120):
    """انتظار حتى يصبح المنفذ متاحًا"""
    logger.info(f"بدء انتظار المنفذ {port}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                logger.info(f"المنفذ {port} متاح")
                return True
        except socket.error:
            logger.debug(f"المنفذ {port} مشغول، انتظار...")
            time.sleep(1)

    logger.error(f"انتهت مهلة انتظار المنفذ {port}")
    return False

def create_app(logger):
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
                 "allow_headers": ["Content-Type", "Authorization"]
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

def main():
    """النقطة الرئيسية لبدء الخادم"""
    try:
        # إعداد التسجيل
        logger = setup_logging()
        logger.info("بدء تشغيل خادم Silvarium Social...")

        # تحميل متغيرات البيئة
        load_dotenv()

        # تحديد المنفذ
        port = int(os.getenv("PORT", "5001"))

        # انتظار المنفذ
        if not wait_for_port(port, logger):
            logger.error("فشل في انتظار المنفذ")
            return 1

        # بدء خادم المقاييس
        metrics_port = port + 1
        prometheus_client.start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")

        # إنشاء التطبيق
        app = create_app(logger)

        # التحقق من الاتصال بقاعدة البيانات
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            conn.close()
            logger.info("تم التحقق من الاتصال بقاعدة البيانات بنجاح")
        except Exception as e:
            logger.error(f"فشل الاتصال بقاعدة البيانات: {str(e)}")
            return 1

        # بدء الخادم
        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")
        serve(
            app,
            host="0.0.0.0",
            port=port,
            url_scheme='https',
            threads=4,
            connection_limit=1000,
            channel_timeout=30
        )

        return 0

    except Exception as e:
        logger.error(f"خطأ غير متوقع: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())