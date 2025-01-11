"""Initialize server package"""
import os
import sys
from flask import Flask
from flask_cors import CORS
from flask_mail import Mail
from flask_login import LoginManager, UserMixin
from datetime import timedelta
import logging
import socket
import time
from logging.handlers import RotatingFileHandler
from server.routes import register_routes
from server.blueprints.admin import admin_bp, init_mail
from dotenv import load_dotenv
from flask_session import Session
from server.database import get_db
from server.blueprints.auth import auth_bp

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
        except Exception as e:
            logger.error(f"Error loading user: {str(e)}")
        finally:
            cur.close()
    return None

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 120) -> bool:
    """Wait for port availability | انتظار جاهزية المنفذ"""
    logger.info(f"بدء انتظار المنفذ {port}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                sock.close()
                logger.info(f"المنفذ {port} متاح")
                print('ready')  # Signal ready for workflow
                return True
        except socket.error:
            time.sleep(1)
            logger.info(f"انتظار المنفذ {port}...")

    logger.error(f"المنفذ {port} غير متاح بعد {timeout} ثانية")
    return False

def create_app(testing=False):
    """Create and configure Flask application"""
    try:
        # Load environment variables first
        load_dotenv()

        # Check required environment variables
        required_vars = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'DATABASE_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"المتغيرات البيئية التالية مفقودة: {', '.join(missing_vars)}")
            return None

        # Setup logging handlers
        if not testing and not os.path.exists('/tmp/logs'):
            os.makedirs('/tmp/logs')
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

            file_handler = RotatingFileHandler(
                '/tmp/logs/silvarium.log',
                maxBytes=1024 * 1024,
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # Get port from environment or config
        port = int(os.getenv('PORT', '5000'))

        # Always wait for port in production mode
        if not testing:
            if not wait_for_port(port):
                logger.error("فشل في انتظار المنفذ")
                return None
            logger.info("تم تأكيد توفر المنفذ بنجاح")

        # Create Flask application with correct static folder path
        static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'client', 'dist'))
        app = Flask(__name__, static_folder=static_folder, static_url_path='/')

        app.config.update(
            DEBUG=os.getenv('FLASK_ENV') == 'development',
            PORT=port,
            HOST='0.0.0.0',
            WAIT_FOR_PORT=True,  # Always wait for port
            WAIT_FOR_PORT_TIMEOUT=120,  # 2 minutes timeout
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME'),
            SESSION_TYPE='filesystem',
            SESSION_PERMANENT=True,
            PERMANENT_SESSION_LIFETIME=timedelta(days=31),
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            SESSION_FILE_DIR='/tmp/flask_session',  # Use tmp directory for session files
            SESSION_FILE_THRESHOLD=500  # Maximum number of session files
        )

        # Setup Session
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])

        # Setup CORS
        CORS(app, supports_credentials=True)

        # Initialize Flask extensions
        mail.init_app(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني بنجاح")

        sess.init_app(app)
        logger.info("تم تهيئة إدارة الجلسات بنجاح")

        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        logger.info("تم تهيئة نظام تسجيل الدخول بنجاح")

        # Initialize database connection
        from server.database import init_db
        db = init_db(app)
        if not db:
            logger.error("فشل في تهيئة قاعدة البيانات")
            return None
        logger.info("تم تهيئة قاعدة البيانات بنجاح")

        # Register blueprints after initializing mail
        init_mail(mail)  # Pass mail instance to admin blueprint
        app.register_blueprint(admin_bp)
        app.register_blueprint(auth_bp)
        logger.info("تم تسجيل المسارات الإدارية ومسارات التحقق بنجاح")

        # Initialize routes
        app = register_routes(app)
        logger.info("تم إعداد المسارات بنجاح")

        logger.info(f"تم تهيئة التطبيق بنجاح على المنفذ {app.config['PORT']}")
        return app

    except Exception as e:
        logger.error(f"خطأ في تهيئة التطبيق: {str(e)}")
        return None

if __name__ == '__main__':
    app = create_app()
    if app:
        port = app.config['PORT']
        app.run(host='0.0.0.0', port=port)