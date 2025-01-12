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

from server.production_config import (
    PRODUCTION_CONFIG,
    APP_CONFIG,
    file_handler,
    LOG_DIR
)
from server.database import init_db, get_db
from server.blueprints.admin import admin_bp, init_mail
from server.blueprints.auth import auth_bp
from server import logger

# إضافة معالج السجلات
logger.addHandler(file_handler)

def cleanup_port(port: int, host: str = '0.0.0.0') -> bool:
    """تنظيف المنفذ إذا كان مشغولاً"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                connections = proc.connections()
                for conn in connections:
                    if hasattr(conn, 'laddr') and conn.laddr.port == port:
                        logger.info(f"إنهاء العملية {proc.pid} التي تستخدم المنفذ {port}")
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                continue
    except Exception as e:
        logger.error(f"خطأ في تنظيف المنفذ: {str(e)}")
    return False

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 120) -> bool:
    """انتظار حتى يصبح المنفذ متاحاً"""
    logger.info(f"بدء انتظار المنفذ {port}... | Starting to wait for port {port}...")
    start_time = time.time()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    while time.time() - start_time < timeout:
        try:
            # محاولة تنظيف المنفذ أولاً
            if cleanup_port(port, host):
                logger.info(f"تم تنظيف المنفذ {port}")
                time.sleep(1)  # انتظار لحظة للتأكد من تحرير المنفذ

            # محاولة ربط المنفذ
            sock.bind((host, port))
            sock.close()
            logger.info(f"المنفذ {port} متاح الآن")
            return True

        except socket.error as e:
            if e.errno == socket.errno.EADDRINUSE:
                logger.debug(f"المنفذ {port} مشغول، انتظار...")
                time.sleep(2)
            else:
                logger.error(f"خطأ غير متوقع في المنفذ: {str(e)}")
                return False

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

        # إنشاء تطبيق Flask
        static_folder = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'client', 'dist'))
        app = Flask(__name__, static_folder=static_folder, static_url_path='/')

        # تطبيق الإعدادات
        app.config.update(APP_CONFIG)
        app.config.update({
            'SESSION_FILE_DIR': '/tmp/flask_session',
            'SESSION_TYPE': 'filesystem',
            'SECRET_KEY': os.getenv('SECRET_KEY', os.urandom(24).hex())
        })

        try:
            # تهيئة المكونات
            components = init_app_components(app)

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
            init_mail(components['mail'])
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

def init_app_components(app: Flask):
    """تهيئة مكونات التطبيق"""
    try:
        components = {}

        # تهيئة قاعدة البيانات
        logger.info("جاري تهيئة قاعدة البيانات...")
        db = init_db(app)
        if not db:
            raise Exception("فشل في تهيئة قاعدة البيانات")
        components['db'] = db
        logger.info("✓ تم تهيئة قاعدة البيانات بنجاح")

        # تهيئة نظام الجلسات
        logger.info("جاري تهيئة نظام الجلسات...")
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])
        session_interface = Session()
        session_interface.init_app(app)
        components['session'] = session_interface
        logger.info("✓ تم تهيئة نظام الجلسات بنجاح")

        # تهيئة خدمة البريد الإلكتروني
        logger.info("جاري تهيئة خدمة البريد الإلكتروني...")
        mail = Mail()
        mail.init_app(app)
        components['mail'] = mail
        logger.info("✓ تم تهيئة خدمة البريد الإلكتروني بنجاح")

        return components

    except Exception as e:
        logger.error(f"خطأ في تهيئة المكونات: {str(e)}", exc_info=True)
        raise

def main():
    """النقطة الرئيسية لبدء الخادم"""
    try:
        # تحديد المتغيرات البيئية
        os.environ['FLASK_ENV'] = 'production'

        # تحديد المنفذ
        DEFAULT_PORT = 5000
        port = int(os.getenv('PORT', str(DEFAULT_PORT)))
        host = '0.0.0.0'

        logger.info(f"بدء تهيئة الخادم على المنفذ {port}")

        # تنظيف وانتظار المنفذ
        if not wait_for_port(port, host, timeout=120):
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
        return 1

if __name__ == "__main__":
    sys.exit(main())