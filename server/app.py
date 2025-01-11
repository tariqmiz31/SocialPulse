"""Flask application factory"""
import os
import sys
import logging
import socket
import time
from flask import Flask, session, g, jsonify
from flask_cors import CORS
from flask_mail import Mail
from flask_login import LoginManager
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from flask_session import Session
from server.database import get_db, init_db
from server.blueprints.admin import admin_bp, init_mail
from server.blueprints.auth import auth_bp
from server import logger, User

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 60) -> bool:
    """انتظار توفر المنفذ مع تسجيل مناسب"""
    start_time = time.time()
    logger.info(f"بدء انتظار المنفذ {port}...")

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.bind((host, port))
                sock.close()
                logger.info(f"المنفذ {port} متاح للاستخدام")
                return True
        except socket.error as e:
            if time.time() - start_time >= timeout:
                logger.error(f"المنفذ {port} غير متاح بعد {timeout} ثانية. السبب: {str(e)}")
                return False
            time.sleep(1)
            logger.debug(f"جاري انتظار المنفذ {port}...")

def init_app_components(app: Flask):
    """تهيئة مكونات التطبيق بالترتيب الصحيح"""
    try:
        # 1. Session
        session_interface = Session()
        session_interface.init_app(app)
        logger.info("تم تهيئة إدارة الجلسات")

        # 2. Database
        db = init_db(app)
        if not db:
            raise Exception("فشل في تهيئة قاعدة البيانات")
        logger.info("تم تهيئة قاعدة البيانات")

        # 3. Login Manager
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'يجب تسجيل الدخول للوصول إلى هذه الصفحة'
        login_manager.login_message_category = 'error'

        @login_manager.user_loader
        def load_user(user_id):
            return User.get(user_id)

        logger.info("تم تهيئة نظام تسجيل الدخول")

        # 4. Mail
        mail = Mail()
        mail.init_app(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني")

        # 5. CORS
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
        logger.info("تم تهيئة CORS")

        return db, mail

    except Exception as e:
        logger.error(f"خطأ في تهيئة مكونات التطبيق: {str(e)}", exc_info=True)
        raise

def create_app(testing=False):
    """Create Flask application with proper initialization sequence"""
    try:
        # Load environment variables
        load_dotenv()

        # Check required environment variables
        required_vars = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'DATABASE_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"المتغيرات البيئية التالية مفقودة: {', '.join(missing_vars)}")
            return None

        # Create Flask app
        static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'client', 'dist'))
        app = Flask(__name__, static_folder=static_folder, static_url_path='/')

        # Basic Configuration
        app.config.update(
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            JSON_AS_ASCII=False,
            SESSION_TYPE='filesystem',
            SESSION_FILE_DIR='/tmp/flask_session',
            SESSION_FILE_THRESHOLD=500,
            SESSION_PERMANENT=True,
            PERMANENT_SESSION_LIFETIME=timedelta(days=1),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME')
        )

        # Ensure session directory exists
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])
            logger.info("تم إنشاء دليل الجلسات")

        try:
            # Initialize components
            db, mail = init_app_components(app)

            # Add database cleanup
            @app.teardown_appcontext
            def cleanup(exc):
                """تنظيف موارد قاعدة البيانات"""
                db = g.pop('db', None)
                if db is not None:
                    db.close()

            # Add request handlers
            @app.before_request
            def before_request():
                """تنفيذ قبل كل طلب"""
                try:
                    g.db = get_db()
                    if 'user_id' in session:
                        session['last_activity'] = time.time()
                        session.modified = True
                except Exception as e:
                    logger.error(f"خطأ في معالجة الطلب: {str(e)}", exc_info=True)
                    return jsonify({"error": "حدث خطأ في معالجة الطلب"}), 500

            # Register blueprints
            init_mail(mail)
            app.register_blueprint(admin_bp)
            app.register_blueprint(auth_bp)
            logger.info("تم تسجيل المسارات")

            # Set application as ready
            app.ready = True
            logger.info("تم تهيئة التطبيق بنجاح وهو جاهز للعمل")

            return app

        except Exception as e:
            logger.error(f"خطأ في إعداد التطبيق: {str(e)}", exc_info=True)
            return None

    except Exception as e:
        logger.error(f"خطأ في تهيئة التطبيق: {str(e)}", exc_info=True)
        return None

def main():
    """The main function to start the server"""
    try:
        # Determine the port
        port = int(os.getenv('PORT', '5000'))
        logger.info(f"بدء تهيئة الخادم على المنفذ {port}")

        # Wait for port availability
        if not wait_for_port(port):
            logger.error(f"فشل في انتظار المنفذ {port}")
            return None, None

        logger.info(f"المنفذ {port} جاهز للاستخدام")

        # Create the application
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return None, None

        # Signal ready for workflow
        print('ready')
        sys.stdout.flush()

        return app, port

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}", exc_info=True)
        return None, None

if __name__ == "__main__":
    app, port = main()
    if app and port:
        app.run(host="0.0.0.0", port=port, debug=True)