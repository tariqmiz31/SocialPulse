"""Initialize server package"""
import os
import sys
import logging
import time
from flask import Flask, session, g, jsonify
from flask_cors import CORS
from flask_mail import Mail
from flask_login import LoginManager, UserMixin
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from flask_session import Session
from server.database import get_db, init_db

# Setup logging
logger = logging.getLogger('silvarium')
logger.setLevel(logging.INFO)

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data[0]
        self.username = user_data[1]
        self.email = user_data[2]
        self.role = user_data[3]
        self.status = user_data[4]

    @staticmethod
    def get(user_id):
        """تحميل المستخدم من قاعدة البيانات"""
        try:
            from .database import get_db
            db = get_db()
            if db:
                cur = db.cursor()
                try:
                    cur.execute("""
                        SELECT id, username, email, role, status
                        FROM users
                        WHERE id = %s AND status = 'active'
                    """, (user_id,))
                    user_data = cur.fetchone()
                    if user_data:
                        return User(user_data)
                finally:
                    cur.close()
        except Exception as e:
            logger.error(f"Error loading user: {str(e)}", exc_info=True)
        return None

def init_extensions(app):
    """تهيئة امتدادات Flask بالترتيب الصحيح"""
    try:
        # تهيئة Session أولاً
        session_interface = Session()
        session_interface.init_app(app)
        logger.info("تم تهيئة إدارة الجلسات")

        # تهيئة نظام تسجيل الدخول
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'يجب تسجيل الدخول للوصول إلى هذه الصفحة'
        login_manager.login_message_category = 'error'

        @login_manager.user_loader
        def load_user(user_id):
            return User.get(user_id)

        logger.info("تم تهيئة نظام تسجيل الدخول")

        # تهيئة خدمة البريد الإلكتروني
        mail = Mail()
        mail.init_app(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني")

        # تهيئة قاعدة البيانات
        db = init_db(app)
        if not db:
            raise Exception("فشل في تهيئة قاعدة البيانات")
        logger.info("تم تهيئة قاعدة البيانات")

        return mail
    except Exception as e:
        logger.error(f"خطأ في تهيئة الامتدادات: {str(e)}", exc_info=True)
        raise

def create_app(testing=False):
    """Create Flask application"""
    try:
        # Load environment variables
        load_dotenv()

        # Create Flask app
        app = Flask(__name__)

        # Basic Configuration
        app.config.update(
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            JSON_AS_ASCII=False,
            SESSION_TYPE='filesystem',
            SESSION_FILE_DIR='/tmp/flask_session',
            PERMANENT_SESSION_LIFETIME=timedelta(days=1),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD')
        )

        try:
            # Initialize extensions
            mail = init_extensions(app)

            # Setup CORS
            CORS(app, 
                 supports_credentials=True,
                 resources={
                     r"/api/*": {
                         "origins": ["http://localhost:5000", "https://*.repl.co"],
                         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                         "allow_headers": ["Content-Type", "Authorization"],
                         "expose_headers": ["Content-Type"],
                         "supports_credentials": True
                     }
                 })

            @app.before_request
            def before_request():
                """تنفيذ قبل كل طلب"""
                try:
                    g.db = get_db()
                    if 'user_id' in session:
                        session.modified = True
                except Exception as e:
                    logger.error(f"خطأ في معالجة الطلب: {str(e)}", exc_info=True)
                    return jsonify({"error": "حدث خطأ في معالجة الطلب"}), 500

            @app.teardown_appcontext
            def teardown_db(exception):
                """تنظيف موارد قاعدة البيانات"""
                db = g.pop('db', None)
                if db is not None:
                    db.close()

            # Register blueprints
            from server.blueprints.admin import admin_bp, init_mail
            from server.blueprints.auth import auth_bp
            from server.blueprints.admin.roles import roles_bp

            init_mail(mail)
            app.register_blueprint(admin_bp)
            app.register_blueprint(auth_bp)
            app.register_blueprint(roles_bp)
            logger.info("تم تسجيل المسارات")

            # Signal ready for workflow
            print('ready')
            sys.stdout.flush()

            return app

        except Exception as e:
            logger.error(f"خطأ في تهيئة التطبيق: {str(e)}", exc_info=True)
            return None

    except Exception as e:
        logger.error(f"خطأ في تهيئة التطبيق: {str(e)}", exc_info=True)
        return None

if __name__ == '__main__':
    app = create_app()
    if app:
        port = int(os.getenv('PORT', '5000'))
        app.run(host='0.0.0.0', port=port)