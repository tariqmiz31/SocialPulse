import sys
import psycopg2
from flask import Flask, request
from flask_cors import CORS
from flask_session import Session
from waitress import serve
import logging
from logging.handlers import RotatingFileHandler
import prometheus_client
from prometheus_client import Counter, Histogram
import socket
import os
import time
import signal
from server.auth import setup_auth
from server.routes import setup_routes
from dotenv import load_dotenv

# تكوين المقاييس
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests')
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP Request Latency')

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

def cleanup_port(port: int, logger):
    """محاولة تحرير المنفذ إذا كان مشغولاً"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.close()
        logger.info(f"تم تحرير المنفذ {port} بنجاح")
        return True
    except Exception as e:
        logger.error(f"فشل في تحرير المنفذ {port}: {str(e)}")
        return False

def is_port_in_use(port: int, logger) -> bool:
    """التحقق مما إذا كان المنفذ قيد الاستخدام"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error as e:
            logger.error(f"خطأ في فحص المنفذ {port}: {str(e)}")
            return True

def wait_for_port(port: int, logger, timeout=120):
    """انتظار حتى يصبح المنفذ متاحًا"""
    logger.info(f"بدء انتظار المنفذ {port}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        if not is_port_in_use(port, logger):
            logger.info(f"المنفذ {port} متاح الآن")
            return True
        if cleanup_port(port, logger):
            logger.info(f"تم تحرير المنفذ {port} بنجاح")
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

    # إضافة مقاييس Prometheus
    @app.before_request
    def before_request():
        REQUEST_COUNT.inc()
        request.start_time = time.time()

    @app.after_request
    def after_request(response):
        REQUEST_LATENCY.observe(time.time() - request.start_time)
        return response

    # إعداد المصادقة والمسارات
    app = setup_auth(app)
    app = setup_routes(app)

    return app

def handle_shutdown(signum, frame, logger):
    """معالجة إشارات إيقاف التشغيل"""
    logger.info("تم استلام إشارة إيقاف التشغيل، جاري إغلاق التطبيق...")
    sys.exit(0)

def start_server():
    """بدء تشغيل الخادم مع التعامل مع الأخطاء وإدارة المنافذ"""
    logger = setup_workflow_logging()
    try:
        # تحميل متغيرات البيئة
        load_dotenv()

        # تسجيل معالجات الإشارات
        signal.signal(signal.SIGTERM, lambda s, f: handle_shutdown(s, f, logger))
        signal.signal(signal.SIGINT, lambda s, f: handle_shutdown(s, f, logger))

        logger.info("بدء تشغيل خادم Silvarium Social...")

        # تحديد المنفذ
        port = int(os.getenv("PORT", "5001"))

        # انتظار حتى يصبح المنفذ متاحًا
        if not wait_for_port(port, logger, timeout=120):
            logger.error(f"فشل في انتظار المنفذ {port}")
            return False

        # بدء خادم المقاييس
        metrics_port = port + 1
        prometheus_client.start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")

        # إنشاء وتكوين التطبيق
        app = create_app()
        logger.info("تم إنشاء التطبيق بنجاح")

        # تأكد من عمل قاعدة البيانات
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            conn.close()
            logger.info("تم التحقق من الاتصال بقاعدة البيانات بنجاح")
        except Exception as e:
            logger.error(f"فشل الاتصال بقاعدة البيانات: {e}")
            return False

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