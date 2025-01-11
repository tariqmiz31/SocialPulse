import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_mail import Mail
from flask_session import Session
from dotenv import load_dotenv
from datetime import timedelta
import socket
import time

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.blueprints.admin import admin_bp, init_mail
from server.routes import register_routes

# تحميل المتغيرات البيئية
load_dotenv()

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

mail = Mail()
sess = Session()

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 120) -> bool:
    """Wait for port availability"""
    start_time = time.time()
    logger.info(f"بدء انتظار المنفذ {port}...")
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                sock.close()
                logger.info(f"المنفذ {port} متاح")
                print('ready')  # Signal ready for workflow
                sys.stdout.flush()
                return True
        except socket.error:
            if time.time() - start_time >= timeout:
                logger.error(f"المنفذ {port} غير متاح بعد {timeout} ثانية")
                return False
            time.sleep(1)
            logger.info(f"انتظار المنفذ {port}...")

def create_app(testing=False):
    """إنشاء تطبيق Flask"""
    try:
        app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

        # إعدادات الجلسة
        app.config.update(
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            SESSION_TYPE='filesystem',
            SESSION_PERMANENT=True,
            PERMANENT_SESSION_LIFETIME=timedelta(days=1),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            SESSION_FILE_DIR='/tmp/flask_session',
            SESSION_FILE_THRESHOLD=500,
            PORT=int(os.getenv('PORT', '5000')),
            WAIT_FOR_PORT=True,
            WAIT_FOR_PORT_TIMEOUT=120
        )

        # تكوين البريد الإلكتروني
        app.config.update(
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME')
        )

        # Create session directory if it doesn't exist
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])

        # تهيئة Flask-Session
        sess.init_app(app)

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

        # Initialize admin blueprint with mail
        init_mail(mail)
        app.register_blueprint(admin_bp)

        @app.before_request
        def before_request():
            # التحقق من صلاحية الجلسة
            if 'user_id' in session and 'last_activity' in session:
                if time.time() - session['last_activity'] > app.config['PERMANENT_SESSION_LIFETIME'].total_seconds():
                    session.clear()
                    return jsonify({'message': 'انتهت صلاحية الجلسة'}), 401
                session['last_activity'] = time.time()
                session.modified = True  # Ensure session changes are saved

        # تسجيل المسارات
        app = register_routes(app)

        logger.info("تم إنشاء تطبيق Flask بنجاح")

        # Signal ready for workflow if configured
        if app.config.get('WAIT_FOR_PORT', False):
            print('ready')
            sys.stdout.flush()

        return app

    except Exception as e:
        logger.error(f"خطأ في إنشاء التطبيق: {str(e)}")
        return None

def main():
    """الدالة الرئيسية لبدء الخادم"""
    try:
        # تحديد المنفذ
        port = int(os.getenv('PORT', '5000'))
        logger.info(f"بدء تهيئة الخادم على المنفذ {port}")

        # انتظار توفر المنفذ
        if not wait_for_port(port):
            logger.error(f"فشل في انتظار المنفذ {port}")
            return None, None

        logger.info(f"المنفذ {port} جاهز للاستخدام")

        # إنشاء التطبيق
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return None, None

        return app, port

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        return None, None

if __name__ == "__main__":
    app, port = main()
    if app and port:
        app.run(host="0.0.0.0", port=port, debug=True)