import os
import sys
from waitress import serve
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import prometheus_client
from prometheus_client import Counter, Histogram
import time
import socket
from flask import Flask, send_from_directory, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash
import psycopg2

# إضافة المسار الرئيسي إلى PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.auth import setup_auth
from server.routes import setup_routes

# تكوين التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

def is_port_in_use(port: int) -> bool:
    """التحقق مما إذا كان المنفذ قيد الاستخدام"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

def wait_for_port(port: int, timeout: int = 60) -> bool:
    """انتظار حتى يصبح المنفذ متاحاً"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            logger.info(f"المنفذ {port} متاح الآن")
            return True
        time.sleep(1)
    return False

def setup_logging():
    """إعداد التسجيل مع التدوير"""
    log_dir = '/tmp/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    file_handler = RotatingFileHandler(
        f'{log_dir}/silvarium.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    logger.addHandler(file_handler)

def create_admin_user():
    """إنشاء حساب المشرف إذا لم يكن موجوداً"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # التحقق من وجود المشرف
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if cur.fetchone() is None:
            # إنشاء مستخدم مشرف جديد
            hashed_password = generate_password_hash('admin123')
            cur.execute(
                """
                INSERT INTO users (username, password, role, is_approved, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ('admin', hashed_password, 'admin', True, 'active')
            )
            conn.commit()
            logger.info("تم إنشاء حساب المشرف بنجاح")

        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في إنشاء حساب المشرف: {e}")

def create_app():
    """إنشاء وإعداد تطبيق Flask"""
    app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

    CORS(app, 
         supports_credentials=True, 
         resources={
             r"/api/*": {
                 "origins": ["https://*.repl.co", "https://*.repl.dev"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"]
             }
         })

    # إعداد المصادقة والمسارات
    app = setup_auth(app)
    app = setup_routes(app)

    return app

def main():
    """الدالة الرئيسية لبدء الخادم"""
    try:
        # تحميل متغيرات البيئة
        load_dotenv()

        # إعداد التسجيل
        setup_logging()
        logger.info("بدء تشغيل خادم الإنتاج...")

        # إنشاء حساب المشرف
        create_admin_user()

        # تحديد المنفذ
        port = int(os.getenv("PORT", "5001"))

        # انتظار حتى يصبح المنفذ متاحاً
        if not wait_for_port(port, timeout=60):
            logger.warning(f"المنفذ {port} مشغول، جاري المحاولة على المنفذ التالي")
            port += 1
            if not wait_for_port(port, timeout=30):
                logger.error(f"لا يمكن العثور على منفذ متاح بعد انتظار 30 ثانية")
                sys.exit(1)

        # إنشاء التطبيق
        app = create_app()

        # تكوين التطبيق
        app.config.update(
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            PERMANENT_SESSION_LIFETIME=1800  # 30 minutes
        )

        # بدء خادم المقاييس
        metrics_port = port + 1
        prometheus_client.start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")

        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")

        # بدء خادم الإنتاج مع waitress
        serve(
            app,
            host="0.0.0.0",
            port=port,
            url_scheme='https',
            threads=4,
            connection_limit=1000,
            channel_timeout=30,
            _quiet=True
        )

        return True
    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {e}")
        raise

if __name__ == "__main__":
    main()