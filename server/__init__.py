"""Initialize server package"""
import os
from flask import Flask
from flask_cors import CORS
from flask_mail import Mail
from datetime import timedelta
import logging
import socket
import time
from logging.handlers import RotatingFileHandler
from server.routes import register_routes
from server.blueprints.admin import admin_bp
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger('silvarium')
logger.setLevel(logging.INFO)

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
                return True
        except socket.error:
            time.sleep(1)
            logger.info(f"انتظار المنفذ {port}...")

    logger.error(f"المنفذ {port} غير متاح بعد {timeout} ثانية")
    return False

# Initialize Flask-Mail
mail = Mail()

def create_app(testing=False):
    """Create and configure Flask application"""
    try:
        # Load environment variables first
        load_dotenv()

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
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME')
        )

        # Setup CORS
        CORS(app, supports_credentials=True)

        # Initialize Flask-Mail
        mail.init_app(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني بنجاح")

        # Initialize database connection
        from server.database import init_db
        db = init_db(app)

        # Register blueprints after initializing mail
        from server.blueprints.admin import admin_bp, init_mail
        init_mail(mail)  # Pass mail instance to admin blueprint
        app.register_blueprint(admin_bp)

        # Initialize routes
        app = register_routes(app)
        logger.info("تم إعداد المسارات بنجاح")

        # Create admin user if needed
        from server.start import create_admin_user
        create_admin_user()

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