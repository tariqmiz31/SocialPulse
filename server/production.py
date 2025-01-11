"""Production Server Configuration"""
import os
import sys
import time
import socket
import logging
import json
import traceback
import signal
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

def try_bind_port(host: str, port: int) -> bool:
    """محاولة ربط المنفذ للتحقق من توفره"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.close()
        return True
    except Exception as e:
        logger.debug(f"فشل في ربط المنفذ {port}: {str(e)}")
        return False

def wait_for_port(host: str, port: int, timeout: int = 120) -> bool:
    """انتظار حتى يصبح المنفذ متاحاً"""
    logger.info(f"بدء انتظار المنفذ {port} على {host}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        if try_bind_port(host, port):
            logger.info(f"المنفذ {port} متاح للاستخدام")
            return True

        logger.debug(f"المنفذ {port} مشغول، انتظار...")
        time.sleep(1)

    logger.error(f"انتهت مهلة انتظار المنفذ {port} بعد {timeout} ثانية")
    return False

def setup_signal_handlers():
    """إعداد معالجات الإشارات"""
    def signal_handler(signum, frame):
        logger.info("تم استلام إشارة إيقاف، جاري إغلاق التطبيق بأمان...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def main() -> int:
    """نقطة الدخول الرئيسية"""
    try:
        # Set production environment and enable port waiting
        os.environ['FLASK_ENV'] = 'production'
        os.environ['WAIT_FOR_PORT'] = 'true'
        os.environ['WAIT_FOR_PORT_TIMEOUT'] = '120'

        logger.info("بدء تشغيل خادم سيلفاريوم الاجتماعي")

        # Use configured port or default to 5000
        try:
            port = int(os.getenv('PORT', '5000'))
        except ValueError:
            logger.warning("قيمة PORT غير صالحة، استخدام المنفذ الافتراضي 5000")
            port = 5000

        host = '0.0.0.0'
        setup_signal_handlers()

        # Wait for port to become available
        if not wait_for_port(host, port, timeout=120):
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

        # Signal ready state
        logger.info('الخادم جاهز للتشغيل')
        print('ready')
        sys.stdout.flush()

        # Start server with waitress
        serve(
            app,
            host=host,
            port=port,
            url_scheme='https',
            threads=4,
            connection_limit=1000,
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