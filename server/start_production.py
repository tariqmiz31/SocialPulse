import os
import sys
from flask import Flask, send_from_directory, request
from waitress import serve
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from flask_cors import CORS
import prometheus_client
from prometheus_client import Counter, Histogram
import time
import socket

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

# إنشاء تطبيق Flask
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

def setup_logging():
    """إعداد التسجيل مع التدوير التلقائي للملفات"""
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

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    """خدمة الملفات الثابتة للتطبيق"""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# مقاييس Prometheus
REQUEST_COUNT = Counter('request_count', 'Total number of requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency in seconds', ['method', 'endpoint'])

@app.before_request
def before_request():
    """تسجيل وقت بدء الطلب"""
    request.start_time = time.time()

@app.after_request
def after_request(response):
    """تسجيل معلومات الطلب ومدته"""
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.path
        ).observe(duration)

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
    return response

def main():
    """الدالة الرئيسية لبدء الخادم"""
    try:
        # تحميل متغيرات البيئة
        load_dotenv()

        # إعداد التسجيل
        setup_logging()
        logger.info("بدء تشغيل خادم الإنتاج...")

        # التحقق من المتغيرات المطلوبة
        if not os.getenv('DATABASE_URL'):
            logger.error("DATABASE_URL غير موجود")
            sys.exit(1)

        # تكوين التطبيق
        app.config.update(
            SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL'),
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24)),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes
            WAIT_FOR_PORT=True
        )

        # تحديد المنفذ
        port = int(os.getenv("PORT", "5001"))

        # انتظار حتى يصبح المنفذ متاحاً
        if not wait_for_port(port):
            logger.warning(f"المنفذ {port} مشغول، جاري المحاولة على المنفذ التالي")
            port += 1

            if not wait_for_port(port):
                raise RuntimeError("لا توجد منافذ متاحة")

        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")
        logger.info(f"تم تكوين قاعدة البيانات: {bool(app.config['SQLALCHEMY_DATABASE_URI'])}")

        # بدء خادم المقاييس
        metrics_port = port + 1
        prometheus_client.start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")

        # بدء خادم الإنتاج مع waitress
        serve(
            app,
            host="0.0.0.0",
            port=port,
            url_scheme='https',
            threads=4,
            connection_limit=1000,
            channel_timeout=30,
            _quiet=True  # تقليل سجلات waitress
        )

        return True
    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {e}")
        raise

if __name__ == "__main__":
    main()