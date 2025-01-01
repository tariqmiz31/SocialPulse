import os
import sys
import socket
import time
from dotenv import load_dotenv
from waitress import serve
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash
import psycopg2
import logging
from logging.handlers import RotatingFileHandler
import prometheus_client
from prometheus_client import Counter, Histogram

# Create Flask app
app = Flask(__name__, static_folder='../client/dist', static_url_path='/')
CORS(app, 
     supports_credentials=True, 
     resources={r"/api/*": {"origins": ["https://*.repl.co", "https://*.repl.dev"]}})

# تكوين التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

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

@app.route('/')
def serve_static():
    """خدمة الملف الرئيسي للتطبيق"""
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def serve_static_paths(path):
    """خدمة المسارات الثابتة للتطبيق"""
    try:
        return app.send_static_file(path)
    except:
        return app.send_static_file('index.html')

def create_admin_user():
    """إنشاء مستخدم مشرف إذا لم يكن موجوداً"""
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
        raise

@app.route('/metrics')
def metrics():
    """نقطة نهاية مقاييس Prometheus"""
    return prometheus_client.generate_latest()

@app.route('/api/admin/status')
def admin_status():
    """نقطة نهاية حالة النظام للمشرفين"""
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'غير مصرح'}), 403

    return jsonify({
        'status': 'running',
        'server_time': time.time(),
        'uptime': time.time() - app.start_time,
        'environment': os.getenv('FLASK_ENV', 'production')
    })

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

# مقاييس Prometheus
REQUEST_COUNT = Counter('request_count', 'Total number of requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency in seconds', ['method', 'endpoint'])


def main():
    try:
        # تحميل متغيرات البيئة
        load_dotenv()

        # إعداد التسجيل
        setup_logging()

        # التحقق من متغيرات البيئة المطلوبة
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
            _quiet=True  # Reduce waitress logging
        )

        return True
    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {e}")
        raise

if __name__ == "__main__":
    main()