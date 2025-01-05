"""Production Server Configuration"""
import os
import sys
import time
import socket
import logging
import json
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

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 120) -> bool:
    """Wait until port becomes available | انتظار حتى يصبح المنفذ متاحاً"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                sock.close()
                logger.info(f"Port {port} is available | المنفذ {port} متاح")
                return True
        except socket.error:
            logger.info(f"Waiting for port {port}... | انتظار المنفذ {port}...")
            time.sleep(1)

    logger.error(f"Port {port} is not available after timeout | المنفذ {port} غير متاح بعد انتهاء المهلة")
    return False

def init_firebase() -> bool:
    """Initialize Firebase | تهيئة Firebase"""
    try:
        if not firebase_admin._apps:
            # Load service account JSON file | تحميل ملف حساب الخدمة
            service_account_path = 'attached_assets/silva-deb1c-firebase-adminsdk-g19p8-5d6dc42cd6.json'

            if not os.path.exists(service_account_path):
                logger.error("Service account file not found | ملف حساب الخدمة غير موجود")
                return False

            with open(service_account_path, 'r') as file:
                cred_dict = json.load(file)

            # Set environment variables from service account file
            os.environ['FIREBASE_PROJECT_ID'] = cred_dict['project_id']
            os.environ['FIREBASE_PRIVATE_KEY'] = cred_dict['private_key']
            os.environ['FIREBASE_CLIENT_EMAIL'] = cred_dict['client_email']

            # Log Firebase initialization
            logger.info(f"Initializing Firebase with project: {cred_dict['project_id']}")
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully | تم تهيئة Firebase بنجاح")

            # Verify initialization
            try:
                firebase_admin.get_app()
                logger.info("Firebase app verification successful")
                return True
            except ValueError:
                logger.error("Firebase app verification failed")
                return False

        return True
    except Exception as e:
        logger.error(f"Firebase initialization error: {str(e)} | خطأ في تهيئة Firebase: {str(e)}")
        return False

def init_server() -> Flask:
    """Initialize Flask server with all configurations | تهيئة خادم Flask مع جميع الإعدادات"""
    try:
        from server import create_app
        app = create_app()
        if not app:
            logger.error("Failed to create Flask application | فشل في إنشاء تطبيق Flask")
            return None

        logger.info("Flask application created successfully")
        return app
    except Exception as e:
        logger.error(f"Server initialization error: {str(e)} | خطأ في تهيئة الخادم: {str(e)}")
        return None

def main() -> int:
    """Main entry point | النقطة الرئيسية لبدء التشغيل"""
    try:
        # Set production mode | تعيين وضع الإنتاج
        os.environ['FLASK_ENV'] = 'production'
        os.environ['WAIT_FOR_PORT'] = 'true'

        # Load environment variables | تحميل المتغيرات البيئية
        load_dotenv()
        logger.info("Starting Silvarium Social server | بدء تشغيل خادم Silvarium Social")

        # Check required environment variables | التحقق من المتغيرات البيئية المطلوبة
        if not os.getenv('DATABASE_URL'):
            logger.error("DATABASE_URL not found | لم يتم العثور على DATABASE_URL")
            return 1

        # Initialize Firebase for SMS verification | تهيئة Firebase للتحقق عبر SMS
        if not init_firebase():
            logger.error("Failed to initialize Firebase | فشل في تهيئة Firebase")
            return 1

        # Get port configuration | الحصول على إعدادات المنفذ
        port = int(os.getenv('PORT', '5000'))

        # Wait for port availability | انتظار توفر المنفذ
        if not wait_for_port(port):
            logger.error(f"Port {port} is not available | المنفذ {port} غير متاح")
            return 1

        # Initialize server | تهيئة الخادم
        app = init_server()
        if not app:
            return 1

        # Signal ready | إشارة الجاهزية
        print('ready')
        sys.stdout.flush()

        # Start production server | بدء خادم الإنتاج
        logger.info(f"Starting production server on port {port}")
        serve(
            app,
            host='0.0.0.0',
            port=port,
            url_scheme='https',
            threads=4,
            channel_timeout=30,
            cleanup_interval=30,
            ident='Silvarium Social'
        )

        return 0

    except Exception as e:
        logger.error(f"Error starting server: {str(e)} | خطأ في بدء تشغيل الخادم: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())