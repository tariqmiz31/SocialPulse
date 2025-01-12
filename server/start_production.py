"""Main production server startup script"""
import os
import sys
import logging
import socket
import time
import signal
import psutil
from flask import Flask, request, jsonify, session, g
from flask_cors import CORS
from flask_mail import Mail
from flask_session import Session
from flask_login import LoginManager
from datetime import timedelta
from dotenv import load_dotenv
from waitress import serve

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.production_config import PRODUCTION_CONFIG, APP_CONFIG, file_handler
from server.database import init_db, get_db
from server.blueprints.admin import admin_bp, init_mail
from server.blueprints.auth import auth_bp
from server import logger

# إضافة معالج السجلات
logger.addHandler(file_handler)

def kill_process_on_port(port: int) -> bool:
    """قتل العملية التي تستخدم المنفذ المحدد"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.connections():
                    if hasattr(conn, 'laddr') and conn.laddr.port == port:
                        logger.info(f"محاولة إنهاء العملية {proc.pid} على المنفذ {port}")
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                            return True
                        except psutil.TimeoutExpired:
                            proc.kill()
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return True
    except Exception as e:
        logger.error(f"خطأ في قتل العملية: {str(e)}")
        return False

def cleanup_port(port: int) -> bool:
    """تنظيف المنفذ بشكل متكرر"""
    attempts = PRODUCTION_CONFIG['port_cleanup_attempts']
    interval = PRODUCTION_CONFIG['port_cleanup_interval']

    for attempt in range(attempts):
        logger.info(f"محاولة تنظيف المنفذ {port} - محاولة {attempt + 1}/{attempts}")

        if kill_process_on_port(port):
            time.sleep(interval)  # انتظار لإتاحة وقت للنظام لتحرير المنفذ

            # التحقق من أن المنفذ متاح الآن
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.bind(('0.0.0.0', port))
                    sock.close()
                    logger.info(f"تم تنظيف المنفذ {port} بنجاح")
                    return True
            except socket.error:
                logger.debug(f"المنفذ {port} لا يزال مشغولاً بعد المحاولة {attempt + 1}")
                time.sleep(interval)
                continue

    logger.error(f"فشل في تنظيف المنفذ {port} بعد {attempts} محاولات")
    return False

def wait_for_port(port: int, timeout: int = 60) -> bool:
    """انتظار حتى يصبح المنفذ متاحاً"""
    logger.info(f"بدء انتظار المنفذ {port}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        # محاولة تنظيف المنفذ أولاً
        if cleanup_port(port):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.bind(('0.0.0.0', port))
                    sock.close()
                    logger.info(f"المنفذ {port} متاح الآن")
                    return True
            except socket.error as e:
                logger.debug(f"فشل في ربط المنفذ {port}: {str(e)}")
                time.sleep(2)
                continue

        logger.debug(f"انتظار المنفذ {port}...")
        time.sleep(2)

    logger.error(f"انتهت مهلة انتظار المنفذ {port}")
    return False

def setup_signal_handlers():
    """إعداد معالجات الإشارات"""
    def signal_handler(signum, frame):
        logger.info("تم استلام إشارة إيقاف، جاري الإغلاق بأمان...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def create_app():
    """إنشاء وتهيئة تطبيق Flask"""
    try:
        # تحميل متغيرات البيئة
        load_dotenv()

        # التحقق من المتغيرات المطلوبة
        required_vars = ['DATABASE_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"المتغيرات البيئية التالية مفقودة: {', '.join(missing_vars)}")
            return None

        app = Flask(__name__)
        app.config.update(APP_CONFIG)

        try:
            # تهيئة قاعدة البيانات
            logger.info("جاري تهيئة قاعدة البيانات...")
            db = init_db(app)
            if not db:
                raise Exception("فشل في تهيئة قاعدة البيانات")
            logger.info("✓ تم تهيئة قاعدة البيانات")

            # تهيئة نظام الجلسات
            logger.info("جاري تهيئة نظام الجلسات...")
            if not os.path.exists('/tmp/flask_session'):
                os.makedirs('/tmp/flask_session')
            session_interface = Session()
            session_interface.init_app(app)
            logger.info("✓ تم تهيئة نظام الجلسات")

            # تهيئة خدمة البريد الإلكتروني
            logger.info("جاري تهيئة خدمة البريد الإلكتروني...")
            mail = Mail()
            mail.init_app(app)
            logger.info("✓ تم تهيئة خدمة البريد الإلكتروني")

            # تهيئة CORS
            logger.info("جاري تهيئة CORS...")
            CORS(app,
                supports_credentials=True,
                resources={
                    r"/api/*": {
                        "origins": ["http://localhost:5000", "https://*.repl.co", "http://0.0.0.0:5000"],
                        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                        "allow_headers": ["Content-Type", "Authorization"],
                        "expose_headers": ["Content-Type"],
                        "supports_credentials": True
                    }
                })
            logger.info("✓ تم تهيئة CORS")

            # تسجيل المسارات
            init_mail(mail)
            app.register_blueprint(admin_bp)
            app.register_blueprint(auth_bp)
            logger.info("✓ تم تسجيل المسارات")

            return app

        except Exception as e:
            logger.error(f"خطأ في إعداد التطبيق: {str(e)}", exc_info=True)
            return None

    except Exception as e:
        logger.error(f"خطأ في تهيئة التطبيق: {str(e)}", exc_info=True)
        return None

def main():
    """النقطة الرئيسية لبدء الخادم"""
    try:
        # تحديد المنفذ
        port = PRODUCTION_CONFIG['port']
        host = PRODUCTION_CONFIG['host']

        logger.info(f"بدء تهيئة الخادم على {host}:{port}")

        # تنظيف وانتظار المنفذ
        if not wait_for_port(port, PRODUCTION_CONFIG['wait_for_port_timeout']):
            logger.error(f"المنفذ {port} غير متاح - إنهاء التطبيق")
            return 1

        # إنشاء وتهيئة التطبيق
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return 1

        # إعداد معالجات الإشارات
        setup_signal_handlers()

        # تأكيد جاهزية التطبيق
        print('ready')
        sys.stdout.flush()
        logger.info("التطبيق جاهز للتشغيل")

        # بدء الخادم
        serve(
            app,
            host=host,
            port=port,
            url_scheme=PRODUCTION_CONFIG['url_scheme'],
            threads=PRODUCTION_CONFIG['threads'],
            connection_limit=PRODUCTION_CONFIG['connection_limit'],
            channel_timeout=PRODUCTION_CONFIG['channel_timeout'],
            cleanup_interval=PRODUCTION_CONFIG['cleanup_interval'],
            ident='Silvarium Social'
        )

        return 0

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())