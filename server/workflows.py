from flask_cors import CORS
from flask import Flask
from waitress import serve
from .app import app, main
import logging
from logging.handlers import RotatingFileHandler
import socket
import os
import time

def setup_workflow_logging():
    """إعداد التسجيل للتدفق العملي"""
    logger = logging.getLogger('silvarium_workflow')
    logger.setLevel(logging.INFO)

    log_dir = '/tmp/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    handler = RotatingFileHandler(
        f'{log_dir}/silvarium_workflow.log',
        maxBytes=1024 * 1024,  # 1MB
        backupCount=3
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    logger.addHandler(handler)
    return logger

def is_port_in_use(port: int) -> bool:
    """التحقق مما إذا كان المنفذ قيد الاستخدام"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

def wait_for_port(port: int, logger, timeout=60):
    """انتظار حتى يصبح المنفذ متاحًا"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            logger.info(f"المنفذ {port} متاح الآن")
            return True
        time.sleep(1)
    return False

def start_server():
    """بدء تشغيل الخادم مع التعامل مع الأخطاء وإدارة المنافذ"""
    logger = setup_workflow_logging()
    try:
        logger.info("بدء تشغيل خادم Silvarium Social...")

        # تحديد المنفذ
        port = int(os.getenv("PORT", "5001"))

        # تعيين متغيرات البيئة للتكوين
        os.environ["WAIT_FOR_PORT"] = "true"
        os.environ["PORT"] = str(port)

        # تكوين التطبيق
        app.config.update(
            WAIT_FOR_PORT=True,
            PORT=port
        )

        # انتظار حتى يصبح المنفذ متاحًا
        if not wait_for_port(port, logger):
            port += 1
            logger.warning(f"تم تغيير المنفذ إلى {port}")
            os.environ["PORT"] = str(port)

            if not wait_for_port(port, logger, timeout=30):
                logger.error("فشل في العثور على منفذ متاح")
                raise RuntimeError("لا توجد منافذ متاحة")

        # بدء التطبيق
        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")
        serve(
            app,
            host="0.0.0.0",
            port=port,
            url_scheme='https',
            threads=4,
            connection_limit=1000,
            channel_timeout=30,
            _quiet=True
        )

        # انتظار حتى يبدأ الخادم
        start_time = time.time()
        while not is_port_in_use(port):
            if time.time() - start_time > 30:
                raise RuntimeError("فشل في بدء الخادم")
            time.sleep(1)

        logger.info("تم بدء الخادم بنجاح")
        return True

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        raise

if __name__ == "__main__":
    start_server()