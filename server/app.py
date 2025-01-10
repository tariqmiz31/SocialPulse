import os
import logging
from logging.handlers import RotatingFileHandler
import prometheus_client
from prometheus_client import Counter, Histogram
import time
import socket
import psycopg2
from werkzeug.security import generate_password_hash
from flask_mail import Mail, Message
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

mail = Mail()

def find_available_port(start_port=5000, max_attempts=10):
    """البحث عن منفذ متاح"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except socket.error:
                continue
    raise RuntimeError("لم يتم العثور على منفذ متاح")

def create_app():
    """إنشاء تطبيق Flask"""
    app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

    # تكوين البريد الإلكتروني
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.getenv('MAIL_USERNAME', 'silvariumsa@gmail.com'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD', 'rtbkamqrxsptmbrl'),
        MAIL_DEFAULT_SENDER='silvariumsa@gmail.com'
    )

    # تهيئة Flask-Mail
    mail.init_app(app)

    # تكوين CORS
    CORS(app, 
         supports_credentials=True,
         resources={
             r"/api/*": {
                 "origins": ["http://localhost:5000", "https://*.repl.co", "https://*.repl.dev"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"]
             }
         })

    # تكوين التسجيل
    if not os.path.exists('logs'):
        os.makedirs('logs')

    file_handler = RotatingFileHandler(
        'logs/silvarium.log',
        maxBytes=10240,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('تم بدء تشغيل سيلفاريوم سوشيال')

    # تكوين Prometheus
    REQUEST_COUNT = Counter('request_count', 'Total number of requests', ['method', 'endpoint', 'status'])
    REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency in seconds', ['method', 'endpoint'])

    @app.before_request
    def before_request():
        request.start_time = time.time()

    @app.after_request
    def after_request(response):
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

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    return app

def main():
    """الدالة الرئيسية لبدء الخادم"""
    try:
        # إنشاء التطبيق
        app = create_app()

        # تحديد المنفذ المتاح
        port = find_available_port()
        logger.info(f"تم العثور على منفذ متاح: {port}")

        # بدء خادم المقاييس
        metrics_port = port + 1
        prometheus_client.start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")

        return app, port

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {e}")
        raise

if __name__ == "__main__":
    app, port = main()
    app.run(host="0.0.0.0", port=port, debug=True)