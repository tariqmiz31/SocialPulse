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

# تكوين التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

def cleanup_port(port: int):
    """محاولة تحرير المنفذ إذا كان مشغولاً"""
    try:
        # Try to create a socket with SO_REUSEADDR
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.close()
        logger.info(f"تم تحرير المنفذ {port} بنجاح")
        return True
    except Exception as e:
        logger.error(f"فشل في تحرير المنفذ {port}: {str(e)}")
        return False

def is_port_in_use(port: int) -> bool:
    """التحقق مما إذا كان المنفذ قيد الاستخدام"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error as e:
            logger.error(f"خطأ في فحص المنفذ {port}: {str(e)}")
            return True

def wait_for_port(port: int, timeout=60):
    """انتظار حتى يصبح المنفذ متاحًا"""
    start_time = time.time()
    logger.info(f"انتظار المنفذ {port}...")

    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            logger.info(f"المنفذ {port} متاح الآن")
            return True
        # محاولة تحرير المنفذ
        if cleanup_port(port):
            return True
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

def handle_shutdown(signum, frame):
    """معالجة إشارات إيقاف التشغيل"""
    logger.info("تم استلام إشارة إيقاف التشغيل، جاري إغلاق التطبيق...")
    sys.exit(0)

def main():
    """الدالة الرئيسية لبدء الخادم"""
    try:
        # تسجيل معالجات الإشارات
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)

        # تحميل متغيرات البيئة
        load_dotenv()

        # تحديد المنفذ
        port = int(os.getenv("PORT", "5001"))

        # انتظار حتى يصبح المنفذ متاحًا
        if not wait_for_port(port, timeout=120):  # زيادة مهلة الانتظار إلى دقيقتين
            logger.error(f"فشل في انتظار المنفذ {port}")
            sys.exit(1)

        # إنشاء التطبيق
        app = create_app()

        # بدء خادم المقاييس
        metrics_port = port + 1
        prometheus_client.start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")

        # تأكد من عمل قاعدة البيانات
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            conn.close()
            logger.info("تم التحقق من الاتصال بقاعدة البيانات بنجاح")
        except Exception as e:
            logger.error(f"فشل الاتصال بقاعدة البيانات: {e}")
            sys.exit(1)

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
            _quiet=False
        )

        return True
    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {e}")
        raise

if __name__ == "__main__":
    main()