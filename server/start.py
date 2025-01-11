"""Main server startup script"""
import os
import sys
import logging
import socket
from dotenv import load_dotenv
from flask import Flask, session, g, jsonify
from flask_cors import CORS
from flask_mail import Mail
from logging.handlers import RotatingFileHandler
import time
import prometheus_client
from flask_session import Session
from datetime import timedelta
from flask_login import LoginManager

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.database import init_db, get_db
from server.blueprints.admin import admin_bp, init_mail
from server.blueprints.auth import auth_bp
from server.blueprints.admin.roles import roles_bp
from server import logger, User

def setup_logging():
    """تهيئة إعدادات التسجيل"""
    if not os.path.exists('logs'):
        os.makedirs('logs')

    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=1024 * 1024,  # 1 MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 60) -> bool:
    """انتظار حتى يصبح المنفذ متاحاً"""
    start_time = time.time()
    logger.info(f"انتظار المنفذ {port} ليصبح متاحاً...")

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result != 0:  # المنفذ متاح
                    logger.info(f"المنفذ {port} متاح")
                    return True
        except socket.error as e:
            logger.error(f"خطأ في فحص المنفذ {port}: {str(e)}")

        if time.time() - start_time > timeout:
            logger.error(f"انتهت مهلة انتظار المنفذ {port}")
            return False

        time.sleep(1)

def create_app(testing=False):
    """إنشاء تطبيق Flask"""
    try:
        # تحميل المتغيرات البيئية وإعداد التسجيل
        load_dotenv()
        setup_logging()

        logger.info("بدء تهيئة التطبيق...")

        # إنشاء تطبيق Flask
        app = Flask(__name__)

        # التكوين الأساسي
        app.config.update(
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            JSON_AS_ASCII=False,
            SESSION_TYPE='filesystem',
            SESSION_FILE_DIR='/tmp/flask_session',
            PERMANENT_SESSION_LIFETIME=timedelta(days=1),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            DEBUG=True if os.getenv('FLASK_ENV') == 'development' else False
        )

        # إنشاء مجلد الجلسات إذا لم يكن موجوداً
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])
            logger.info("تم إنشاء مجلد الجلسات")

        # تهيئة إدارة الجلسات
        Session(app)
        logger.info("تم تهيئة إدارة الجلسات")

        # تهيئة مدير تسجيل الدخول
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'يجب تسجيل الدخول للوصول إلى هذه الصفحة'
        login_manager.login_message_category = 'error'

        @login_manager.user_loader
        def load_user(user_id):
            return User.get(user_id)

        logger.info("تم تهيئة مدير تسجيل الدخول")

        # تهيئة خدمة البريد الإلكتروني إذا كانت المتغيرات البيئية متوفرة
        if os.getenv('MAIL_USERNAME') and os.getenv('MAIL_PASSWORD'):
            app.config.update(
                MAIL_SERVER='smtp.gmail.com',
                MAIL_PORT=587,
                MAIL_USE_TLS=True,
                MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
                MAIL_PASSWORD=os.getenv('MAIL_PASSWORD')
            )
            mail = Mail(app)
            logger.info("تم تهيئة خدمة البريد الإلكتروني")
        else:
            mail = None
            logger.warning("لم يتم تكوين خدمة البريد الإلكتروني")

        # تهيئة قاعدة البيانات
        db = init_db(app)
        if not db:
            raise Exception("فشل في تهيئة قاعدة البيانات")
        logger.info("تم تهيئة قاعدة البيانات")

        # إعداد CORS
        CORS(app,
             supports_credentials=True,
             resources={
                 r"/api/*": {
                     "origins": ["http://localhost:8080", "https://*.repl.co"],
                     "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                     "allow_headers": ["Content-Type", "Authorization"],
                     "expose_headers": ["Content-Type"],
                     "supports_credentials": True
                 }
             })
        logger.info("تم تطبيق إعدادات CORS")

        # تسجيل المسارات البرمجية
        if mail:
            init_mail(mail)
        app.register_blueprint(admin_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(roles_bp)
        logger.info("تم تسجيل المسارات البرمجية")

        @app.before_request
        def before_request():
            """إعداد اتصال قاعدة البيانات لكل طلب"""
            try:
                g.db = get_db()
                if g.db is None:
                    return jsonify({"error": "فشل الاتصال بقاعدة البيانات"}), 500
            except Exception as e:
                logger.error(f"خطأ في معالجة الطلب: {str(e)}")
                return jsonify({"error": "حدث خطأ في معالجة الطلب"}), 500

        @app.errorhandler(500)
        def handle_500(error):
            logger.error(f"خطأ في الخادم: {str(error)}")
            return jsonify({
                "error": "حدث خطأ في الخادم",
                "details": str(error) if app.debug else None
            }), 500

        return app

    except Exception as e:
        logger.error(f"خطأ في تهيئة التطبيق: {str(e)}")
        return None

def main():
    """نقطة الدخول الرئيسية"""
    try:
        # الحصول على رقم المنفذ من المتغيرات البيئية
        port = int(os.getenv('PORT', '8080'))

        # انتظار حتى يصبح المنفذ متاحاً
        if not wait_for_port(port):
            logger.error(f"المنفذ {port} غير متاح")
            return 1

        # إنشاء وتكوين التطبيق
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return 1

        # إعداد خادم المقاييس
        metrics_port = port + 1
        try:
            prometheus_client.start_http_server(metrics_port)
            logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")
        except Exception as e:
            logger.warning(f"فشل في بدء خادم المقاييس: {str(e)}")

        # الإشارة إلى جاهزية التطبيق
        print('ready')
        sys.stdout.flush()

        # بدء الخادم
        app.run(host='0.0.0.0', port=port)
        return 0

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())