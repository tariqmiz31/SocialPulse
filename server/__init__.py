"""Initialize server package"""
import os
from flask import Flask
from flask_cors import CORS
from flask_session import Session
from datetime import timedelta
import logging
from logging.handlers import RotatingFileHandler

from server.monitoring import setup_monitoring
from server.auth import setup_auth
from server.routes import setup_routes

def create_app():
    app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

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
    app.config.update(
        SESSION_TYPE='filesystem',
        SESSION_COOKIE_SECURE=True if os.getenv('FLASK_ENV') == 'production' else False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=1),
        SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
        DEBUG=os.getenv('FLASK_ENV') != 'production',
        PORT=int(os.getenv('PORT', '8080')),
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

    # إعداد الجلسة
    Session(app)

    # إعداد المكونات بالترتيب الصحيح
    app = setup_routes(app)   # أولاً: إعداد المسارات العامة
    app = setup_auth(app)     # ثانياً: إعداد المصادقة
    app = setup_monitoring(app)  # ثالثاً: إعداد المراقبة

    # تسجيل بدء تشغيل التطبيق
    logger.info('تم تهيئة التطبيق بنجاح')
    logger.info(f'التطبيق مكون للعمل على {app.config["HOST"]}:{app.config["PORT"]}')

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', '8080'))
    app.run(host='0.0.0.0', port=port)