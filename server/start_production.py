#!/usr/bin/env python3
import os
import sys
from waitress import serve
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import socket
import time

# إضافة مسار المشروع إلى PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from server import create_app

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

def wait_for_port_available(port: int, retries: int = 5, delay: int = 2) -> bool:
    """انتظار حتى يصبح المنفذ متاحاً"""
    for i in range(retries):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            return True
        except socket.error:
            if i < retries - 1:
                time.sleep(delay)
            sock.close()
    return False

def main():
    """النقطة الرئيسية لبدء الخادم"""
    logger = setup_logging()
    logger.info("بدء تشغيل خادم Silvarium Social...")

    try:
        load_dotenv()

        host = "0.0.0.0"
        port = int(os.getenv("PORT", "8080"))

        logger.info(f"محاولة بدء الخادم على {host}:{port}")

        # انتظار حتى يصبح المنفذ متاحاً
        if not wait_for_port_available(port):
            logger.error(f"المنفذ {port} غير متاح بعد عدة محاولات")
            return 1

        app = create_app()

        # بدء الخادم باستخدام waitress
        logger.info(f"بدء الخادم على {host}:{port}")
        serve(
            app,
            host=host,
            port=port,
            threads=4,
            channel_timeout=30,
            cleanup_interval=30,
            ident='Silvarium Social'
        )

        return 0

    except Exception as e:
        logger.error(f"خطأ غير متوقع: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())