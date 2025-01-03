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
import traceback

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

def kill_process_on_port(port, logger):
    """قتل العملية التي تستخدم المنفذ المحدد"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.connections():
                    if conn.laddr.port == port:
                        logger.info(f"وجدت عملية (PID: {proc.pid}) تستخدم المنفذ {port}")
                        proc.terminate()
                        time.sleep(1)
                        if proc.is_running():
                            proc.kill()
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"خطأ في قتل العملية: {str(e)}")
    return False

def cleanup_port(port: int, logger):
    """تنظيف المنفذ إذا كان مشغولاً"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()

        if result == 0:  # المنفذ مشغول
            logger.info(f"المنفذ {port} مشغول، محاولة تحريره")
            if kill_process_on_port(port, logger):
                logger.info(f"تم تحرير المنفذ {port} بنجاح")
            else:
                logger.warning(f"فشل في تحرير المنفذ {port}")
    except Exception as e:
        logger.error(f"خطأ في تنظيف المنفذ: {str(e)}")

def wait_for_port(port: int, host: str, logger, timeout=30):
    """انتظار حتى يصبح المنفذ متاحاً"""
    cleanup_port(port, logger)  # تنظيف المنفذ أولاً

    start_time = time.time()
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind((host, port))
                logger.info(f"المنفذ {port} متاح للاستخدام")
                sock.close()
                return True
            except socket.error:
                sock.close()
                if time.time() - start_time > timeout:
                    logger.error(f"انتهت مهلة انتظار المنفذ {port}")
                    return False
                time.sleep(1)
                continue
        except Exception as e:
            logger.error(f"خطأ في انتظار المنفذ: {str(e)}")
            return False

def signal_handler(signum, frame):
    """معالج إشارات النظام"""
    logger = logging.getLogger('silvarium_production')
    logger.info(f"تم استلام الإشارة {signum}")
    sys.exit(0)

def main():
    """النقطة الرئيسية لبدء الخادم"""
    logger = setup_logging()
    logger.info("بدء تشغيل خادم Silvarium Social...")

    try:
        # تسجيل معالجات الإشارات
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        load_dotenv()

        host = "0.0.0.0"
        port = int(os.getenv("PORT", "8080"))

        logger.info(f"محاولة بدء الخادم على {host}:{port}")

        # تنظيف وانتظار المنفذ
        if not wait_for_port(port, host, logger):
            logger.error(f"فشل في تحرير المنفذ {port}")
            return 1

        # إنشاء التطبيق
        app = create_app()

        logger.info(f"تم إنشاء التطبيق بنجاح، بدء الخادم على {host}:{port}")
        serve(
            app,
            host=host,
            port=port,
            threads=4,
            connection_limit=1000,
            channel_timeout=30,
            cleanup_interval=30,
            url_scheme='http',
            _quiet=False  # إضافة هذا لطباعة السجلات
        )

        return 0

    except Exception as e:
        logger.error(f"خطأ غير متوقع: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())