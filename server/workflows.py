"""Workflow configuration and management"""
import os
import sys
import socket
import time
import logging
import psutil
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS
from waitress import serve

# إعداد التسجيل
logger = logging.getLogger('silvarium_workflow')
logger.setLevel(logging.INFO)

if not os.path.exists('/tmp/logs'):
    os.makedirs('/tmp/logs')

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler = RotatingFileHandler('/tmp/logs/workflow.log', maxBytes=10*1024*1024, backupCount=5)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def cleanup_ports():
    """تنظيف المنافذ المشغولة"""
    port = int(os.getenv('PORT', '5000'))  # تحديث المنفذ الافتراضي إلى 5000
    logger.info(f"بدء تنظيف المنفذ {port}...")

    try:
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.connections():
                    if hasattr(conn, 'laddr') and conn.laddr.port == port:
                        logger.info(f"إنهاء العملية {proc.pid} على المنفذ {port}")
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return True
    except Exception as e:
        logger.error(f"خطأ في تنظيف المنافذ: {str(e)}")
        return False

def wait_for_port(timeout=120):
    """انتظار حتى يصبح المنفذ متاحاً"""
    port = int(os.getenv('PORT', '5000'))  # تحديث المنفذ الافتراضي إلى 5000
    logger.info(f"انتظار المنفذ {port}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # محاولة تنظيف المنفذ أولاً
            if not cleanup_ports():
                logger.warning("فشل في تنظيف المنفذ، المحاولة مرة أخرى...")

            # محاولة ربط المنفذ
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', port))
                logger.info(f"المنفذ {port} متاح الآن")
                return True
        except socket.error:
            logger.debug(f"المنفذ {port} مشغول، انتظار...")
            time.sleep(2)
            continue

    logger.error(f"فشل في انتظار المنفذ {port} بعد {timeout} ثانية")
    return False

def create_app():
    """إنشاء وتهيئة تطبيق الورك فلو"""
    app = Flask(__name__)

    # تكوين CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["https://*.repl.co", "http://0.0.0.0:5000"],  # تحديث المنفذ إلى 5000
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    return app

def start_workflow():
    """بدء تشغيل التدفق العملي"""
    try:
        # تنظيف المنافذ المشغولة
        if not cleanup_ports():
            logger.warning("تحذير: فشل في تنظيف المنافذ")

        # انتظار حتى يصبح المنفذ متاحاً
        if not wait_for_port():
            return False

        port = int(os.getenv('PORT', '5000'))  # تحديث المنفذ الافتراضي إلى 5000
        app = create_app()

        # إشارة الجاهزية للتدفق العملي
        print('ready')
        sys.stdout.flush()

        # بدء الخادم
        logger.info(f"بدء التدفق العملي على المنفذ {port}")
        serve(
            app,
            host='0.0.0.0',
            port=port,
            url_scheme='https',
            threads=4,
            connection_limit=1000,
            channel_timeout=30,
            cleanup_interval=30
        )
        return True

    except Exception as e:
        logger.error(f"خطأ في بدء التدفق العملي: {str(e)}")
        return False

if __name__ == "__main__":
    success = start_workflow()
    sys.exit(0 if success else 1)