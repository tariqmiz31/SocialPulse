#!/usr/bin/env python3
import os
import sys
from waitress import serve
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import time
import socket
import signal
import psutil

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

    # إعداد تسجيل الملف
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

def cleanup_port(port: int, logger):
    """تنظيف المنفذ إذا كان مشغولاً"""
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.connections():
                if conn.laddr.port == port:
                    logger.info(f"إيقاف العملية {proc.pid} التي تستخدم المنفذ {port}")
                    psutil.Process(proc.pid).terminate()
                    time.sleep(1)  # انتظار لإغلاق العملية
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

def wait_for_port(port: int, host: str, logger, timeout=30):
    """انتظار حتى يصبح المنفذ متاحاً"""
    cleanup_port(port, logger)  # تنظيف المنفذ أولاً

    start_time = time.time()
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                logger.info(f"المنفذ {port} متاح للاستخدام")
                return True
        except socket.error:
            if time.time() - start_time > timeout:
                logger.error(f"انتهت مهلة انتظار المنفذ {port}")
                return False
            time.sleep(1)
            continue

def signal_handler(signum, frame):
    """معالج إشارات النظام"""
    logger = logging.getLogger('silvarium_production')
    logger.info(f"تم استلام الإشارة {signum}")
    sys.exit(0)

def main():
    """النقطة الرئيسية لبدء الخادم"""
    try:
        logger = setup_logging()
        logger.info("بدء تشغيل خادم Silvarium Social...")

        # تسجيل معالجات الإشارات
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        load_dotenv()

        host = "0.0.0.0"
        port = int(os.getenv("PORT", "3000"))

        if not wait_for_port(port, host, logger):
            logger.error(f"فشل في انتظار المنفذ {port}")
            return 1

        app = create_app()

        logger.info(f"بدء تشغيل الخادم على {host}:{port}")
        serve(
            app,
            host=host,
            port=port,
            threads=4,
            connection_limit=1000,
            channel_timeout=30,
            cleanup_interval=30,
            url_scheme='http'
        )
        return 0

    except Exception as e:
        if 'logger' in locals():
            logger.error(f"خطأ غير متوقع: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())