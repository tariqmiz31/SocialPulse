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

# تكوين التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

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

# مقاييس Prometheus
REQUEST_COUNT = Counter('request_count', 'Total number of requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency in seconds', ['method', 'endpoint'])

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    """خدمة الملفات الثابتة للتطبيق"""
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

def main():
    """الدالة الرئيسية لبدء الخادم"""
    try:
        # تحميل متغيرات البيئة
        load_dotenv()

        # إعداد التسجيل
        setup_logging()
        logger.info("بدء تشغيل خادم الإنتاج...")

        # تحديد المنفذ
        port = int(os.getenv("PORT", "5001"))

        # بدء خادم المقاييس
        metrics_port = port + 1
        prometheus_client.start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")

        # تكوين التطبيق
        app.config.update(
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            PERMANENT_SESSION_LIFETIME=1800  # 30 minutes
        )

        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")

        # بدء خادم الإنتاج مع waitress
        serve(
            app,
            listen=f'*:{port}'
        )

        return True
    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {e}")
        raise

if __name__ == "__main__":
    main()