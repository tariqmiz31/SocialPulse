"""Flask application factory"""
import os
import sys
import logging
from flask import Flask, session, g, jsonify
from flask_cors import CORS
from flask_mail import Mail
from flask_login import LoginManager
from datetime import timedelta
from dotenv import load_dotenv
from flask_session import Session
from server.database import get_db, init_db
from server.blueprints.admin import admin_bp, init_mail
from server.blueprints.auth import auth_bp
from server import logger, User

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
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME'),
            WAIT_FOR_PORT=True
        )

        # Ensure session directory exists
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])
            logger.info("تم إنشاء دليل الجلسات")

        # 1. Initialize Session first
        session_interface = Session()
        session_interface.init_app(app)
        logger.info("تم تهيئة إدارة الجلسات")

        # 2. Initialize Login Manager
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'يجب تسجيل الدخول للوصول إلى هذه الصفحة'
        login_manager.login_message_category = 'error'

        @login_manager.user_loader
        def load_user(user_id):
            return User.get(user_id)

        logger.info("تم تهيئة نظام تسجيل الدخول")

        # 3. Initialize Mail
        mail = Mail()
        mail.init_app(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني")

        # Setup CORS
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

        # Initialize database
        db = init_db(app)
        if not db:
            logger.error("فشل في تهيئة قاعدة البيانات")
            return None
        logger.info("تم الاتصال بقاعدة البيانات")

        @app.before_request
        def before_request():
            """Execute before each request"""
            try:
                g.db = get_db()
                if 'user_id' in session:
                    session['last_activity'] = time.time()
                    session.modified = True
            except Exception as e:
                logger.error(f"خطأ في معالجة الطلب: {str(e)}", exc_info=True)
                return jsonify({"error": "حدث خطأ في معالجة الطلب"}), 500

        @app.teardown_appcontext
        def teardown_db(exception):
            """Clean up database resources"""
            db = g.pop('db', None)
            if db is not None:
                db.close()

        # Register blueprints
        init_mail(mail)
        app.register_blueprint(admin_bp)
        app.register_blueprint(auth_bp)
        logger.info("تم تسجيل المسارات")

        # Signal ready for workflow
        print('ready')
        sys.stdout.flush()

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
                return True
        except socket.error:
            if time.time() - start_time >= timeout:
                logger.error(f"المنفذ {port} غير متاح بعد {timeout} ثانية")
                return False
            time.sleep(1)
            logger.info(f"انتظار المنفذ {port}...")

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

        return app, port

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}", exc_info=True)
        return None, None

import socket
if __name__ == "__main__":
    app, port = main()
    if app and port:
        app.run(host="0.0.0.0", port=port, debug=True)