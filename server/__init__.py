"""Initialize server package"""
import os
import sys
import logging
from flask import Flask, session, g
from flask_cors import CORS
from flask_mail import Mail
from flask_login import LoginManager, UserMixin
from datetime import timedelta
import logging
from logging.handlers import RotatingFileHandler
from server.routes import register_routes
from server.blueprints.admin import admin_bp, init_mail
from dotenv import load_dotenv
from flask_session import Session
from server.database import get_db, init_db
from server.blueprints.auth import auth_bp
import socket
import time

# Setup logging
logger = logging.getLogger('silvarium')
logger.setLevel(logging.INFO)

# Initialize Flask extensions
mail = Mail()
sess = Session()
login_manager = LoginManager()

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data[0]
        self.username = user_data[1]
        self.email = user_data[2]
        self.role = user_data[3]
        self.status = user_data[4]

@login_manager.user_loader
def load_user(user_id):
    """تحميل المستخدم من قاعدة البيانات"""
    try:
        db = get_db()
        if db:
            cur = db.cursor()
            try:
                cur.execute("""
                    SELECT id, username, email, role, status
                    FROM users
                    WHERE id = %s AND status = 'active'
                """, (user_id,))
                user_data = cur.fetchone()
                if user_data:
                    return User(user_data)
            finally:
                cur.close()
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
    return None

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 120) -> bool:
    """Wait for port availability"""
    start_time = time.time()
    logger.info(f"بدء انتظار المنفذ {port}...")

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                sock.close()  # Make sure to close the socket
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
    """Create Flask application"""
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

        # Configure app
        app.config.update(
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            SESSION_TYPE='filesystem',
            SESSION_PERMANENT=True,
            PERMANENT_SESSION_LIFETIME=timedelta(days=1),
            SESSION_FILE_DIR='/tmp/flask_session',
            SESSION_FILE_THRESHOLD=500,
            SESSION_COOKIE_SECURE=False,  # Set to False for development
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME'),
            JSON_AS_ASCII=False,
            WAIT_FOR_PORT=True,
            WAIT_FOR_PORT_TIMEOUT=120
        )

        # Setup Session directory
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])

        # Initialize Flask extensions in the correct order
        mail.init_app(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني بنجاح")

        sess.init_app(app)
        logger.info("تم تهيئة إدارة الجلسات بنجاح")

        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        logger.info("تم تهيئة نظام تسجيل الدخول بنجاح")

        # Setup CORS with proper configuration
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
        logger.info("تم الاتصال بقاعدة البيانات بنجاح")

        @app.before_request
        def before_request():
            g.db = get_db()

        @app.teardown_appcontext
        def teardown_db(exception):
            db = g.pop('db', None)
            if db is not None:
                db.close()

        # Register blueprints after all configurations
        init_mail(mail)
        app.register_blueprint(admin_bp)
        app.register_blueprint(auth_bp)
        logger.info("تم تسجيل المسارات الإدارية ومسارات التحقق بنجاح")

        # Signal ready for workflow
        print('ready')
        sys.stdout.flush()

        return app

    except Exception as e:
        logger.error(f"خطأ في تهيئة التطبيق: {str(e)}")
        return None

if __name__ == '__main__':
    app = create_app()
    if app:
        port = int(os.getenv('PORT', '5000'))
        if wait_for_port(port):
            app.run(host='0.0.0.0', port=port)