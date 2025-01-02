"""Initialize server package"""
import os
from flask import Flask
from flask_cors import CORS
from flask_session import Session
from datetime import timedelta
import logging
from logging.handlers import RotatingFileHandler
from server.monitoring import setup_monitoring

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

    # تكوين CORS
    CORS(app, 
         supports_credentials=True, 
         resources={
             r"/api/*": {
                 "origins": ["*"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "expose_headers": ["Content-Range", "X-Content-Range"],
                 "supports_credentials": True
             }
         })

    # تكوين الجلسة
    app.config.update(
        SESSION_TYPE='filesystem',
        SESSION_COOKIE_SECURE=True if os.getenv('FLASK_ENV') == 'production' else False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=1),
        SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
        DEBUG=os.getenv('FLASK_ENV') != 'production'
    )
    Session(app)

    from server.auth import setup_auth
    from server.routes import setup_routes

    # إعداد المصادقة والمسارات
    app = setup_auth(app)
    app = setup_routes(app)

    # إعداد المراقبة
    metrics_port = int(os.getenv('METRICS_PORT', '9090'))
    app = setup_monitoring(app, metrics_port=metrics_port)

    # تسجيل بدء تشغيل التطبيق
    logger.info('تم بدء تشغيل التطبيق بنجاح')

    return app

app = create_app()

if __name__ == '__main__':
    # تكوين سجلات Flask
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    app.run(host='0.0.0.0', port=3000, debug=True)