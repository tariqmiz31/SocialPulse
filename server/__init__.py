"""Initialize server package"""
import os
from flask import Flask
from flask_cors import CORS
from flask_session import Session
from datetime import timedelta
import logging
from logging.handlers import RotatingFileHandler
from server.routes import setup_routes
from server.blueprints.auth import auth_bp, init_auth
from server.config import config

def create_app():
    """إنشاء وتكوين تطبيق Flask"""
    app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

    # تحديد بيئة التشغيل
    env = os.getenv('FLASK_ENV', 'production')
    app_config = config[env]

    # إعداد التسجيل
    logger = logging.getLogger('silvarium')
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')

    # إعداد تسجيل الملف
    log_dir = '/tmp/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    file_handler = RotatingFileHandler(
        f'{log_dir}/silvarium.log',
        maxBytes=1024 * 1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # إضافة تسجيل وحدة التحكم
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # تكوين التطبيق
    port = int(os.getenv('PORT', '8080'))  # Use PORT environment variable with default 8080
    app.config.update(
        SESSION_TYPE=app_config.SESSION_TYPE,
        SESSION_FILE_DIR=app_config.SESSION_FILE_DIR,
        SESSION_COOKIE_SECURE=app_config.SESSION_COOKIE_SECURE,
        SESSION_COOKIE_HTTPONLY=app_config.SESSION_COOKIE_HTTPONLY,
        SESSION_COOKIE_SAMESITE=app_config.SESSION_COOKIE_SAMESITE,
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=app_config.PERMANENT_SESSION_LIFETIME),
        SECRET_KEY=app_config.SECRET_KEY,
        DEBUG=app_config.DEBUG,
        PORT=port,
        HOST='0.0.0.0'
    )

    # إعداد CORS
    CORS(app, 
         supports_credentials=True,
         resources={
             r"/api/*": {
                 "origins": [
                     "http://localhost:8080",
                     "https://localhost:8080",
                     os.getenv('APP_URL', 'https://silvariumsocial.com')
                 ],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "expose_headers": ["Content-Range", "X-Content-Range"],
                 "supports_credentials": True
             }
         })

    # إعداد المصادقة
    app = init_auth(app)
    app.register_blueprint(auth_bp)

    # إنشاء مجلد الجلسات إذا لم يكن موجوداً
    session_dir = app_config.SESSION_FILE_DIR
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)

    # إعداد الجلسة
    Session(app)

    # إعداد المسارات
    app = setup_routes(app)

    # تسجيل بدء تشغيل التطبيق
    logger.info('تم تهيئة التطبيق بنجاح | Application initialized successfully')
    logger.info(f'التطبيق مكون للعمل على {app.config["HOST"]}:{app.config["PORT"]} | Application configured to run on {app.config["HOST"]}:{app.config["PORT"]}')

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', '8080'))
    app.run(host='0.0.0.0', port=port)