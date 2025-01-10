import os
import psycopg2
from dotenv import load_dotenv
from flask import Flask, request, send_from_directory
from flask_cors import CORS
import logging
from werkzeug.security import generate_password_hash
import socket
import prometheus_client
from prometheus_client import Counter, Histogram
import time

# تكوين التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

def create_admin_user():
    """إنشاء حساب المشرف Tariq"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # إنشاء المستخدم المشرف
        cur.execute("""
            INSERT INTO users (username, password, role, is_approved, status)
            VALUES (%s, %s, 'admin', true, 'active')
            ON CONFLICT (username) 
            DO UPDATE SET 
                password = EXCLUDED.password,
                role = 'admin',
                is_approved = true,
                status = 'active'
            RETURNING id;
        """, ('Tariq', generate_password_hash('admin123')))

        user_id = cur.fetchone()[0]
        conn.commit()

        print(f"تم إنشاء حساب المشرف Tariq بنجاح (ID: {user_id})")
        return user_id

    except Exception as e:
        print(f"خطأ في إنشاء حساب المشرف: {str(e)}")
        raise
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def create_app():
    """إنشاء وتكوين تطبيق Flask"""
    app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

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

    # Serve static files and handle frontend routing
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
        # تحميل متغيرات البيئة
        load_dotenv()

        # التحقق من متغيرات البيئة المطلوبة
        if not os.getenv('DATABASE_URL'):
            raise ValueError("DATABASE_URL غير موجود")

        # إنشاء/تحديث مستخدم مشرف
        create_admin_user()

        # إنشاء التطبيق
        app = create_app()

        # تحديد المنفذ
        port = int(os.getenv('PORT', 5000))

        # بدء خادم المقاييس
        metrics_port = port + 1
        prometheus_client.start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")

        # Ready signal for workflow
        print('ready')

        # بدء الخادم
        app.run(host="0.0.0.0", port=port, debug=True)

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {e}")
        raise

if __name__ == "__main__":
    main()