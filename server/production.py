"""Production server configuration and startup"""
import os
import sys
import socket
import time
import logging
import signal
import psutil
import traceback
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS
from waitress import serve

# إعداد التسجيل
logger = logging.getLogger('silvarium_production')
logger.setLevel(logging.INFO)

if not os.path.exists('/tmp/logs'):
    os.makedirs('/tmp/logs')

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler = RotatingFileHandler('/tmp/logs/production.log', maxBytes=10*1024*1024, backupCount=5)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def cleanup_ports():
    """تنظيف المنافذ المشغولة"""
    port = int(os.getenv('PORT', '8080'))
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
    port = int(os.getenv('PORT', '8080'))
    logger.info(f"انتظار المنفذ {port}...")
    start_time = time.time()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    while time.time() - start_time < timeout:
        try:
            # محاولة تنظيف المنفذ أولاً
            if cleanup_ports():
                logger.info(f"تم تنظيف المنفذ {port}")
                time.sleep(1)  # انتظار لحظة للتأكد من تحرير المنفذ

            # محاولة ربط المنفذ
            sock.bind(('0.0.0.0', port))
            sock.close()
            logger.info(f"المنفذ {port} متاح الآن")
            return True

        except socket.error as e:
            if e.errno == socket.errno.EADDRINUSE:
                logger.debug(f"المنفذ {port} مشغول، انتظار...")
                time.sleep(2)
            else:
                logger.error(f"خطأ غير متوقع: {str(e)}")
                return False

    logger.error(f"فشل في انتظار المنفذ {port} بعد {timeout} ثانية")
    return False

def create_app():
    """إنشاء وتهيئة تطبيق Flask"""
    app = Flask(__name__)

    # تكوين CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["https://*.repl.co", "http://0.0.0.0:8080"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    return app

def setup_signal_handlers():
    """إعداد معالجات الإشارات"""
    def signal_handler(signum, frame):
        logger.info("تم استلام إشارة إيقاف، جاري الإغلاق بأمان...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def main():
    """النقطة الرئيسية لبدء الخادم"""
    try:
        # تنظيف المنافذ المشغولة
        if not cleanup_ports():
            logger.warning("تحذير: فشل في تنظيف المنافذ")

        # انتظار حتى يصبح المنفذ متاحاً
        if not wait_for_port():
            return 1

        port = int(os.getenv('PORT', '8080'))
        app = create_app()

        # إعداد معالجات الإشارات
        setup_signal_handlers()

        # تأكيد جاهزية التطبيق
        logger.info('الخادم جاهز للتشغيل')
        print('ready')
        sys.stdout.flush()

        # بدء الخادم
        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")
        serve(
            app,
            host='0.0.0.0',
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