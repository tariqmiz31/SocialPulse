from flask_cors import CORS
from flask import Flask
from waitress import serve
from .start import app, main
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
        port = int(os.getenv("PORT", "5001"))

        # انتظار حتى يصبح المنفذ متاحًا
        if not wait_for_port(port, logger):
            port += 1  # تجربة المنفذ التالي إذا كان المنفذ الحالي مشغولاً
            logger.warning(f"تم تغيير المنفذ إلى {port}")

            if not wait_for_port(port, logger, timeout=30):
                logger.error("فشل في العثور على منفذ متاح")
                raise RuntimeError("لا توجد منافذ متاحة")

        # تحديث متغير البيئة بالمنفذ الجديد
        os.environ["PORT"] = str(port)

        # بدء التطبيق
        app.config['wait_for_port'] = True
        app.config['port'] = port
        main()
        logger.info(f"تم بدء الخادم بنجاح على المنفذ {port}")

        # انتظار حتى يصبح المنفذ مشغولاً (يعني أن الخادم بدأ بنجاح)
        start_time = time.time()
        while not is_port_in_use(port):
            if time.time() - start_time > 30:
                raise RuntimeError("فشل في بدء الخادم")
            time.sleep(1)

        return True
    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        raise

if __name__ == "__main__":
    start_server()