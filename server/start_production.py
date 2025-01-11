"""Main production server startup script"""
import os
import sys
import logging
import socket
import time
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

def is_port_in_use(port: int, host: str = '0.0.0.0') -> bool:
    """التحقق من استخدام المنفذ"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return False
        except socket.error:
            return True

def wait_for_port(port=5000, host='0.0.0.0', timeout=60):
    """انتظار حتى يصبح المنفذ متاحاً"""
    logger.info(f"بدء انتظار المنفذ {port}... | Starting to wait for port {port}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        if not is_port_in_use(port, host):
            logger.info(f"المنفذ {port} متاح للاستخدام | Port {port} is available")
            return True
        logger.debug(f"المنفذ {port} مشغول، انتظار... | Port {port} is busy, waiting...")
        time.sleep(1)

    logger.error(f"المنفذ {port} غير متاح بعد {timeout} ثانية | Port {port} not available after {timeout} seconds")
    return False

def init_app_components(app: Flask):
    """تهيئة مكونات التطبيق بالترتيب الصحيح مع التحقق من كل خطوة"""
    with app.app_context():
        try:
            components = {}

            # 1. تهيئة قاعدة البيانات
            logger.info("جاري تهيئة قاعدة البيانات...")
            db = init_db(app)
            if not db:
                raise Exception("فشل في تهيئة قاعدة البيانات")
            components['db'] = db
            logger.info("✓ تم تهيئة قاعدة البيانات بنجاح")

            # 2. تهيئة نظام الجلسات
            logger.info("جاري تهيئة نظام الجلسات...")
            if not os.path.exists(app.config['SESSION_FILE_DIR']):
                os.makedirs(app.config['SESSION_FILE_DIR'])
            session_interface = Session()
            session_interface.init_app(app)
            components['session'] = session_interface
            logger.info("✓ تم تهيئة نظام الجلسات بنجاح")

            # 3. تهيئة خدمة البريد الإلكتروني
            logger.info("جاري تهيئة خدمة البريد الإلكتروني...")
            mail = Mail()
            mail.init_app(app)
            components['mail'] = mail
            logger.info("✓ تم تهيئة خدمة البريد الإلكتروني بنجاح")

            return components

        except Exception as e:
            logger.error(f"خطأ في تهيئة المكونات: {str(e)}", exc_info=True)
            raise

def create_app():
    """إنشاء وتهيئة تطبيق Flask مع التحقق المناسب من كل خطوة"""
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
            with app.app_context():
                # تهيئة المكونات الأساسية
                components = init_app_components(app)

                # تهيئة CORS
                logger.info("جاري تهيئة CORS...")
                CORS(app, 
                    supports_credentials=True,
                    resources={
                        r"/api/*": {
                            "origins": ["http://localhost:8080", "https://*.repl.co", "http://0.0.0.0:8080"],
                            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                            "allow_headers": ["Content-Type", "Authorization"],
                            "expose_headers": ["Content-Type"],
                            "supports_credentials": True
                        }
                    })
                logger.info("✓ تم تهيئة CORS بنجاح")

                # تسجيل المسارات
                logger.info("جاري تسجيل المسارات...")
                init_mail(components['mail'])
                app.register_blueprint(admin_bp)
                app.register_blueprint(auth_bp)
                logger.info("✓ تم تسجيل المسارات بنجاح")

                # نقطة نهاية حالة الخادم
                @app.route('/api/server/status')
                def server_status():
                    """التحقق من حالة الخادم"""
                    return jsonify({
                        'status': 'running',
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'ready': True,
                        'components_status': {
                            'database': bool(g.get('db')),
                            'mail': bool(components.get('mail')),
                            'session': bool(components.get('session'))
                        }
                    })

                # إضافة معالجات الطلبات
                @app.before_request
                def before_request():
                    """تنفيذ قبل كل طلب"""
                    try:
                        g.db = get_db()
                        if g.db is None:
                            return jsonify({"error": "فشل الاتصال بقاعدة البيانات"}), 500
                    except Exception as e:
                        logger.error(f"خطأ في معالجة الطلب: {str(e)}")
                        return jsonify({"error": "حدث خطأ في معالجة الطلب"}), 500

                app.ready = True
                logger.info("✓ تم تهيئة التطبيق بنجاح وهو جاهز للعمل")
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
        # Set environment variables for port waiting
        os.environ['WAIT_FOR_PORT'] = 'true'
        os.environ['WAIT_FOR_PORT_TIMEOUT'] = '120'  # 2 minutes timeout

        # تحديد المنفذ
        port = int(os.getenv('PORT', '5000'))
        logger.info(f"بدء تهيئة الخادم على المنفذ {port}")

        # إنشاء وتهيئة التطبيق
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return 1

        # انتظار حتى يصبح المنفذ متاحاً
        if not wait_for_port(port=port, timeout=120):
            logger.error(f"المنفذ {port} غير متاح بعد انتهاء المهلة")
            return 1

        # تأكيد جاهزية التطبيق
        print('ready')
        sys.stdout.flush()
        logger.info("التطبيق جاهز للتشغيل")

        # بدء الخادم باستخدام waitress
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
        logger.error(f"خطأ في بدء الخادم: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())