"""Main server startup script"""
import os
import sys
import psycopg2
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_mail import Mail
import logging
from werkzeug.security import generate_password_hash
import prometheus_client
from prometheus_client import Counter, Histogram
import time
from logging.handlers import RotatingFileHandler
from server.blueprints.admin import admin_bp

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server import create_app, logger

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

        logger.info(f"تم إنشاء حساب المشرف Tariq بنجاح (ID: {user_id})")
        return user_id

    except Exception as e:
        logger.error(f"خطأ في إنشاء حساب المشرف: {str(e)}")
        raise
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def main():
    """نقطة البداية الرئيسية | Main entry point"""
    try:
        # تحميل متغيرات البيئة
        load_dotenv()

        # Create Flask application
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return 1

        # Register admin blueprint
        app.register_blueprint(admin_bp)

        # تكوين البريد الإلكتروني
        app.config.update(
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME')
        )

        # تهيئة Flask-Mail
        mail = Mail(app)
        mail.init_app(app)


        # إعداد ملف السجل
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

        # تكوين نقاط النهاية
        from server.routes import register_routes
        register_routes(app)

        # إنشاء/تحديث مستخدم مشرف
        create_admin_user()


        # Signal ready
        logger.info('الخادم جاهز | Server is ready')
        print('ready')
        sys.stdout.flush()

        # Start server
        port = app.config['PORT']
        app.run(host='0.0.0.0', port=port)
        return 0

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())