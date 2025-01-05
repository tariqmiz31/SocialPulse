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

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup logging
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

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 30) -> bool:
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
            time.sleep(1)

    logger.error(f"Port {port} is not available | المنفذ {port} غير متاح")
    return False

def find_available_port(start_port: int = 5000, max_attempts: int = 10) -> int:
    """Find an available port | البحث عن منفذ متاح"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', port))
                sock.close()
                logger.info(f"Found available port: {port}")
                return port
        except socket.error:
            continue
    raise RuntimeError(f"No available ports found between {start_port} and {start_port + max_attempts}")

def main() -> int:
    """Main entry point | النقطة الرئيسية لبدء التشغيل"""
    try:
        # Set production environment
        os.environ['FLASK_ENV'] = 'production'
        os.environ['WAIT_FOR_PORT'] = 'true'

        logger.info("Starting Silvarium Social production server")

        # Use configured port or find available one
        try:
            port = int(os.getenv('PORT', '5000'))
        except ValueError:
            logger.warning("Invalid PORT environment variable, using default port 5000")
            port = 5000

        if not wait_for_port(port):
            logger.warning(f"Port {port} is not available, searching for available port...")
            try:
                port = find_available_port(5000)
            except RuntimeError as e:
                logger.error(str(e))
                return 1

        # Create Flask app
        logger.info("Creating Flask application | إنشاء تطبيق Flask")
        from server import create_app
        app = create_app()
        if not app:
            logger.error("Failed to create Flask application | فشل في إنشاء تطبيق Flask")
            return 1

        # Signal ready
        logger.info('Server is ready | الخادم جاهز')
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
        logger.error(f"Error starting server: {str(e)} | خطأ في بدء تشغيل الخادم: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())