from flask import Flask, send_from_directory, request, session, jsonify
from flask_cors import CORS
from waitress import serve
import os
import logging
from logging.handlers import RotatingFileHandler
import prometheus_client
from prometheus_client import Counter, Histogram
import time
import socket
import psycopg2
from werkzeug.security import generate_password_hash

# إعداد التسجيل
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
             "methods": ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
             "allow_headers": ['Content-Type', 'Authorization']
         }
     })

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

    # إضافة رؤوس CORS
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """خدمة الملفات الثابتة للتطبيق"""
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

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

def main():
    """الدالة الرئيسية لبدء الخادم"""
    try:
        # التحقق من متغيرات البيئة
        if not os.getenv('DATABASE_URL'):
            raise ValueError("DATABASE_URL غير موجود")

        # تكوين التطبيق
        app.config.update(
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            PERMANENT_SESSION_LIFETIME=1800,
            WAIT_FOR_PORT=True  # إضافة إعداد انتظار المنفذ
        )

        # إنشاء مستخدم مشرف
        create_admin_user()

        # تحديد المنفذ
        port = int(os.getenv("PORT", "5001"))

        # انتظار حتى يصبح المنفذ متاحاً
        if app.config['WAIT_FOR_PORT']:
            if not wait_for_port(port):
                logger.warning(f"المنفذ {port} مشغول، جاري المحاولة على المنفذ التالي")
                port += 1

                if not wait_for_port(port):
                    raise RuntimeError("لا توجد منافذ متاحة")

        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")

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
            _quiet=True
        )

        return True
    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {e}")
        raise

if __name__ == "__main__":
    main()