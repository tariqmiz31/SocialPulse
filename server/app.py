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
        MAIL_SERVER=os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
        MAIL_PORT=int(os.getenv('MAIL_PORT', '587')),
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.getenv('MAIL_DEFAULT_SENDER', 'no-reply@silvariumsocial.com')
    )

    # تهيئة Flask-Mail
    mail.init_app(app)

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

    async def send_verification_email(to_email: str, code: str):
        """إرسال بريد التحقق"""
        try:
            msg = Message(
                'تأكيد البريد الإلكتروني - سيلفاريوم سوشيال',
                recipients=[to_email],
                html=f"""
                <div dir="rtl" style="text-align: right; font-family: Arial, sans-serif;">
                    <h2>مرحباً بك في سيلفاريوم سوشيال</h2>
                    <p>شكراً لتسجيلك معنا. للتحقق من بريدك الإلكتروني، يرجى إدخال الرمز التالي في التطبيق:</p>
                    <div style="background-color: #f4f4f4; padding: 15px; margin: 20px 0; font-size: 24px; text-align: center;">
                        {code}
                    </div>
                    <p>هذا الرمز صالح لمدة 24 ساعة.</p>
                    <p>إذا لم تقم بطلب هذا التحقق، يرجى تجاهل هذا البريد الإلكتروني.</p>
                    <p>مع تحيات فريق سيلفاريوم سوشيال</p>
                </div>
                """
            )
            mail.send(msg)
            logger.info(f"تم إرسال رمز التحقق إلى {to_email}")
            return True
        except Exception as e:
            logger.error(f"خطأ في إرسال البريد الإلكتروني: {str(e)}")
            return False

    return app

def create_admin_user():
    """إنشاء مستخدم مشرف إذا لم يكن موجوداً"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # التحقق من وجود المشرف
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
        logger.info(f"تم تحديث حساب المشرف Tariq بنجاح (ID: {user_id})")

    except Exception as e:
        logger.error(f"خطأ في إنشاء/تحديث حساب المشرف: {e}")
        raise
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def main():
    """الدالة الرئيسية لبدء الخادم"""
    try:
        # تحديد المنفذ المتاح
        port = find_available_port()
        logger.info(f"تم العثور على منفذ متاح: {port}")

        # إنشاء وتكوين التطبيق
        app = create_app()

        # بدء خادم المقاييس
        metrics_port = port + 1
        prometheus_client.start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")

        # إنشاء مستخدم مشرف
        create_admin_user()

        return app, port

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {e}")
        raise

if __name__ == "__main__":
    app, port = main()
    app.run(host="0.0.0.0", port=port, debug=True)