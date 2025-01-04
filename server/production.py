"""Production Server Configuration"""
import os
import sys
import time
import socket
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS
from waitress import serve
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

def setup_logging():
    """Sets up logging with rotation | إعداد التسجيل مع التدوير"""
    log_dir = '/tmp/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger('silvarium_production')
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    )

    file_handler = RotatingFileHandler(
        f'{log_dir}/silvarium.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 60) -> bool:
    """Wait until port becomes available | انتظار حتى يصبح المنفذ متاحاً"""
    start_time = time.time()

    # Keep checking until timeout
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result != 0:  # Port is available
                    logger.info(f"Port {port} is available | المنفذ {port} متاح")
                    return True
                else:  # Port is in use
                    logger.info(f"Waiting for port {port}... | انتظار المنفذ {port}...")
                    time.sleep(1)
        except Exception as e:
            logger.error(f"Error checking port {port}: {str(e)} | خطأ في فحص المنفذ {port}: {str(e)}")
            return False

    logger.error(f"Port {port} is not available after timeout | المنفذ {port} غير متاح بعد انتهاء المهلة")
    return False

def init_firebase() -> bool:
    """Initialize Firebase | تهيئة Firebase"""
    try:
        service_account_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'attached_assets',
            'silva-11e9d-firebase-adminsdk-n8a88-74bc434752.json'
        )

        if not os.path.exists(service_account_path):
            logger.error("Firebase service account file not found | ملف حساب خدمة Firebase غير موجود")
            return False

        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully | تم تهيئة Firebase بنجاح")

        return True
    except Exception as e:
        logger.error(f"Firebase initialization error: {str(e)} | خطأ في تهيئة Firebase: {str(e)}")
        return False

def main() -> bool:
    """Main entry point | النقطة الرئيسية لبدء التشغيل"""
    try:
        # Set production mode
        os.environ['FLASK_ENV'] = 'production'
        os.environ['WAIT_FOR_PORT'] = 'true'  # Enable port waiting

        load_dotenv()
        logger.info("Starting Silvarium Social server | بدء تشغيل خادم Silvarium Social")

        # Check for required environment variables
        if not os.getenv('DATABASE_URL'):
            logger.error("DATABASE_URL not found | لم يتم العثور على DATABASE_URL")
            return False

        # Initialize Firebase for SMS verification
        if not init_firebase():
            logger.error("Failed to initialize Firebase | فشل في تهيئة Firebase")
            return False

        # Create Flask app with production config
        from server import create_app
        app = create_app()
        if not app:
            logger.error("Failed to create Flask application | فشل في إنشاء تطبيق Flask")
            return False

        port = int(os.getenv("PORT", "8080"))

        # Always wait for port in production
        if not wait_for_port(port, timeout=60):
            logger.error(f"Port {port} is not available after timeout | المنفذ {port} غير متاح بعد انتهاء المهلة")
            return False

        # Signal that we're ready to accept connections
        print("ready")
        sys.stdout.flush()

        logger.info(f"Starting server on port {port} | بدء تشغيل الخادم على المنفذ {port}")

        # Start the production server with waitress
        serve(
            app,
            host="0.0.0.0",
            port=port,
            url_scheme='https',
            threads=4,
            channel_timeout=30,
            cleanup_interval=30,
            ident='Silvarium Social'
        )

        return True

    except Exception as e:
        logger.error(f"Error starting server: {str(e)} | خطأ في بدء تشغيل الخادم: {str(e)}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)