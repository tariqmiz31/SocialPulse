"""Main server startup script"""
import os
import sys
import logging
import socket
import time
from dotenv import load_dotenv
from flask import Flask, session, g, jsonify, current_app
from flask_cors import CORS
from flask_mail import Mail
from logging.handlers import RotatingFileHandler
import prometheus_client
from prometheus_flask_exporter import PrometheusMetrics
from flask_session import Session
from datetime import timedelta
from flask_login import LoginManager

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.database import init_db, get_db
from server.blueprints.admin import admin_bp, init_mail
from server.blueprints.auth import auth_bp
from server.blueprints.admin.roles import roles_bp
from server import logger, User

def setup_logging():
    """تهيئة إعدادات التسجيل"""
    if not os.path.exists('logs'):
        os.makedirs('logs')

    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=1024 * 1024,  # 1 MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.info("تم تهيئة نظام التسجيل")

def create_app(testing=False):
    """إنشاء تطبيق Flask"""
    try:
        # تحميل المتغيرات البيئية وإعداد التسجيل
        load_dotenv()
        setup_logging()

        logger.info("بدء تهيئة التطبيق...")

        # إنشاء تطبيق Flask
        app = Flask(__name__)

        # إضافة مقاييس Prometheus
        metrics = PrometheusMetrics(app)
        metrics.info('app_info', 'Application info', version='1.0.0')

        # التكوين الأساسي
        app.config.update(
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            JSON_AS_ASCII=False,
            SESSION_TYPE='filesystem',
            SESSION_FILE_DIR='/tmp/flask_session',
            PERMANENT_SESSION_LIFETIME=timedelta(days=1),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            DEBUG=True if os.getenv('FLASK_ENV') == 'development' else False
        )

        # إنشاء مجلد الجلسات إذا لم يكن موجوداً
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])
            logger.info("تم إنشاء مجلد الجلسات")

        # تهيئة إدارة الجلسات
        Session(app)
        logger.info("تم تهيئة إدارة الجلسات")

        # تهيئة مدير تسجيل الدخول
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'يجب تسجيل الدخول للوصول إلى هذه الصفحة'
        login_manager.login_message_category = 'error'

        @login_manager.user_loader
        def load_user(user_id):
            return User.get(user_id)

        logger.info("تم تهيئة مدير تسجيل الدخول")

        # تهيئة قاعدة البيانات
        db = init_db(app)
        if not db:
            raise Exception("فشل في تهيئة قاعدة البيانات")
        logger.info("تم تهيئة قاعدة البيانات")

        # إعداد CORS
        CORS(app,
             supports_credentials=True,
             resources={
                 r"/api/*": {
                     "origins": ["http://localhost:8080", "https://*.repl.co"],
                     "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                     "allow_headers": ["Content-Type", "Authorization"],
                     "expose_headers": ["Content-Type"],
                     "supports_credentials": True
                 }
             })
        logger.info("تم تطبيق إعدادات CORS")

        # تسجيل المسارات البرمجية
        from server.routes import register_routes
        register_routes(app)
        logger.info("تم تسجيل المسارات الأساسية")

        app.register_blueprint(admin_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(roles_bp)
        logger.info("تم تسجيل جميع المسارات البرمجية")

        @app.before_request
        def before_request():
            """إعداد اتصال قاعدة البيانات لكل طلب"""
            try:
                g.db = get_db()
                if g.db is None:
                    logger.error("فشل الاتصال بقاعدة البيانات")
                    return jsonify({"error": "فشل الاتصال بقاعدة البيانات"}), 500
            except Exception as e:
                logger.error(f"خطأ في معالجة الطلب: {str(e)}")
                return jsonify({"error": "حدث خطأ في معالجة الطلب"}), 500

        @app.errorhandler(500)
        def handle_500(error):
            logger.error(f"خطأ في الخادم: {str(error)}")
            return jsonify({
                "error": "حدث خطأ في الخادم",
                "details": str(error) if app.debug else None
            }), 500

        # إشارة الجاهزية
        print("ready")
        sys.stdout.flush()
        logger.info("تم تهيئة التطبيق بنجاح")

        return app

    except Exception as e:
        logger.error(f"خطأ في تهيئة التطبيق: {str(e)}")
        return None

if __name__ == "__main__":
    try:
        # الحصول على رقم المنفذ من المتغيرات البيئية
        port = int(os.getenv('PORT', '8080'))
        logger.info(f"بدء تشغيل التطبيق على المنفذ {port}")

        # إنشاء وتكوين التطبيق
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            sys.exit(1)

        # إعداد خادم المقاييس
        metrics_port = port + 1
        try:
            prometheus_client.start_http_server(metrics_port)
            logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")
        except Exception as e:
            logger.warning(f"فشل في بدء خادم المقاييس: {str(e)}")

        # بدء الخادم
        app.run(host='0.0.0.0', port=port)

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        sys.exit(1)