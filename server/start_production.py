"""Main production server startup script"""
import os
import sys
import time
import socket
from waitress import serve
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import signal
import prometheus_client
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server import create_app
from server.config import config

def setup_logging():
    """إعداد التسجيل"""
    log_dir = '/tmp/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger('silvarium_production')
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    file_handler = RotatingFileHandler(
        f'{log_dir}/silvarium.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 30) -> bool:
    """انتظار حتى يصبح المنفذ متاحاً"""
    logger = logging.getLogger('silvarium_production')
    start_time = time.time()
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                logger.info(f"المنفذ {port} متاح للاستخدام | Port {port} is available")
                return True
        except socket.error:
            if time.time() - start_time >= timeout:
                logger.error(f"المنفذ {port} غير متاح | Port {port} is not available")
                return False
            logger.info(f"انتظار المنفذ {port}... | Waiting for port {port}...")
            time.sleep(1)

def main():
    """النقطة الرئيسية لبدء الخادم"""
    # إعداد التسجيل
    logger = setup_logging()
    logger.info("بدء تشغيل خادم Silvarium Social... | Starting Silvarium Social server...")

    try:
        # تحميل المتغيرات البيئية والتكوين
        load_dotenv()
        env = os.getenv('FLASK_ENV', 'production')
        app_config = config[env]

        # تكوين الخادم
        host = '0.0.0.0'
        port = int(os.getenv('PORT', '8080'))

        logger.info(f"محاولة بدء الخادم على {host}:{port} | Attempting to start server on {host}:{port}")

        # انتظار حتى يصبح المنفذ متاحاً
        if not wait_for_port(port):
            return 1

        # إنشاء تطبيق Flask
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask | Failed to create Flask application")
            return 1

        # تشغيل الخادم
        serve(
            app,
            host=host,
            port=port,
            url_scheme='https',
            threads=4,
            channel_timeout=30,
            cleanup_interval=30,
            ident='Silvarium Social'
        )

        # إرسال إشارة جاهزية
        print('ready')
        sys.stdout.flush()

        # استمرار تشغيل الخادم
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("تم استلام إشارة إيقاف، إغلاق التطبيق... | Received shutdown signal, closing application...")

        return 0

    except Exception as e:
        logger.error(f"خطأ غير متوقع: {str(e)} | Unexpected error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())