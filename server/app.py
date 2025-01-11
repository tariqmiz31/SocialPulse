import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, session, g
from flask_cors import CORS
from flask_mail import Mail
from flask_session import Session
from flask_login import LoginManager
from dotenv import load_dotenv
from datetime import timedelta
import time
import socket

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.blueprints.admin import admin_bp, init_mail
from server.routes import register_routes
from server.database import init_db, get_db
from server import logger, User

def init_extensions(app):
    """تهيئة امتدادات Flask بالترتيب الصحيح"""
    try:
        # 1. تهيئة Session أولاً
        flask_session = Session()
        flask_session.init_app(app)
        logger.info("تم تهيئة إدارة الجلسات")

        # 2. تهيئة نظام تسجيل الدخول
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'

        @login_manager.user_loader
        def load_user(user_id):
            return User.get(user_id)

        logger.info("تم تهيئة نظام تسجيل الدخول")

        # 3. تهيئة خدمة البريد الإلكتروني
        flask_mail = Mail()
        flask_mail.init_app(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني")

        return flask_session, login_manager, flask_mail
    except Exception as e:
        logger.error(f"خطأ في تهيئة الامتدادات: {str(e)}", exc_info=True)
        raise

def create_app(testing=False):
    """إنشاء تطبيق Flask"""
    try:
        # تحميل المتغيرات البيئية
        load_dotenv()

        # التحقق من المتغيرات البيئية المطلوبة
        required_vars = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'DATABASE_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"المتغيرات البيئية التالية مفقودة: {', '.join(missing_vars)}")
            return None

        # إنشاء تطبيق Flask
        app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

        # الإعدادات الأساسية
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
        app.config['JSON_AS_ASCII'] = False

        # إعدادات الجلسة
        app.config.update(
            SESSION_TYPE='filesystem',
            SESSION_FILE_DIR='/tmp/flask_session',
            SESSION_FILE_THRESHOLD=500,
            SESSION_PERMANENT=True,
            PERMANENT_SESSION_LIFETIME=timedelta(days=1),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax'
        )

        # إعدادات البريد الإلكتروني
        app.config.update(
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME')
        )

        # التأكد من وجود مجلد الجلسات
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])
            logger.info("تم إنشاء دليل الجلسات")

        # تهيئة الامتدادات
        flask_session, login_manager, flask_mail = init_extensions(app)

        # تكوين CORS
        CORS(app, 
             supports_credentials=True,
             resources={
                 r"/api/*": {
                     "origins": ["http://localhost:5000", "https://*.repl.co", "http://0.0.0.0:5000"],
                     "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                     "allow_headers": ["Content-Type", "Authorization"],
                     "expose_headers": ["Content-Type"],
                     "supports_credentials": True
                 }
             })

        # تهيئة قاعدة البيانات
        db = init_db(app)
        if not db:
            logger.error("فشل في تهيئة قاعدة البيانات")
            return None
        logger.info("تم الاتصال بقاعدة البيانات")

        @app.before_request
        def before_request():
            """تنفيذ قبل كل طلب"""
            try:
                g.db = get_db()

                # تحديث وقت النشاط في الجلسة
                if 'user_id' in session:
                    session['last_activity'] = time.time()
                    session.modified = True
            except Exception as e:
                logger.error(f"خطأ في معالجة الطلب: {str(e)}", exc_info=True)
                return jsonify({"error": "حدث خطأ في معالجة الطلب"}), 500

        @app.teardown_appcontext
        def teardown_db(exception):
            """تنظيف موارد قاعدة البيانات"""
            db = g.pop('db', None)
            if db is not None:
                db.close()

        # تسجيل المسارات
        init_mail(flask_mail)
        app.register_blueprint(admin_bp)
        logger.info("تم تسجيل المسارات")

        # تكوين التسجيل (من الكود الأصلي)
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


        return app

    except Exception as e:
        logger.error(f"خطأ في تهيئة التطبيق: {str(e)}", exc_info=True)
        return None

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
        logger.error(f"خطأ في بدء الخادم: {str(e)}", exc_info=True)
        return None, None

if __name__ == "__main__":
    app, port = main()
    if app and port:
        app.run(host="0.0.0.0", port=port, debug=True)