"""Production Server Configuration"""
import os
import sys
import time
import socket
import logging
import json
import traceback
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS
from waitress import serve

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup logging first
logger = logging.getLogger('silvarium_production')
logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
if not os.path.exists('/tmp/logs'):
    os.makedirs('/tmp/logs')

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

file_handler = RotatingFileHandler(
    '/tmp/logs/silvarium.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def is_port_in_use(port: int, host: str = '0.0.0.0') -> bool:
    """Check if port is already in use | التحقق من استخدام المنفذ"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return False
        except socket.error:
            return True

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 60) -> bool:
    """Wait for port availability | انتظار حتى يصبح المنفذ متاحاً"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_port_in_use(port, host):
            logger.info(f"المنفذ {port} متاح | Port {port} is available")
            return True
        logger.info(f"انتظار المنفذ {port}... | Waiting for port {port}...")
        time.sleep(1)

    logger.error(f"المنفذ {port} غير متاح بعد {timeout} ثانية | Port {port} not available after {timeout} seconds")
    return False

def main() -> int:
    """Main entry point | نقطة الدخول الرئيسية"""
    try:
        # Set production environment and enable port waiting
        os.environ['FLASK_ENV'] = 'production'
        os.environ['WAIT_FOR_PORT'] = 'true'  # Always wait for port in production
        os.environ['WAIT_FOR_PORT_TIMEOUT'] = '120'  # 2 minutes timeout

        logger.info("بدء تشغيل خادم سيلفاريوم الاجتماعي | Starting Silvarium Social production server")

        # Use configured port or default to 5000
        try:
            port = int(os.getenv('PORT', '5000'))
        except ValueError:
            logger.warning("قيمة PORT غير صالحة، استخدام المنفذ الافتراضي 5000")
            port = 5000

        # Wait for port to become available
        if not wait_for_port(port, timeout=120):
            logger.error(f"المنفذ {port} غير متاح - إنهاء التطبيق")
            return 1

        # Create Flask app
        logger.info("إنشاء تطبيق Flask")
        from server import create_app
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return 1

        # Initialize verification tables
        from server.blueprints.auth import init_verification_tables
        if not init_verification_tables():
            logger.error("فشل في تهيئة جداول التحقق")
            return 1
        logger.info("تم تهيئة جداول التحقق بنجاح")

        # Signal ready
        logger.info('الخادم جاهز | Server is ready')
        print('ready')
        sys.stdout.flush()

        # Start server with waitress
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
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())