import os
import sys
from waitress import serve
import logging
from logging.handlers import RotatingFileHandler
import socket
import time
from dotenv import load_dotenv
import signal
from flask import Flask
from flask_cors import CORS

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

def setup_logging():
    """إعداد التسجيل"""
    log_dir = '/tmp/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger('silvarium_production')
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    file_handler = RotatingFileHandler(
        f'{log_dir}/silvarium.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def wait_for_port_available(port: int, max_retries: int = 30, delay: int = 1) -> bool:
    """انتظار حتى يصبح المنفذ متاحاً"""
    logger = logging.getLogger('silvarium_production')
    for i in range(max_retries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('0.0.0.0', port))
                sock.close()  # Close the socket after testing
                logger.info(f"المنفذ {port} متاح للاستخدام")
                return True
            except socket.error:
                if i < max_retries - 1:
                    logger.warning(f"المنفذ {port} مشغول، محاولة {i+1}/{max_retries}. انتظار {delay} ثوانٍ...")
                    time.sleep(delay)
                else:
                    logger.error(f"فشل في الوصول إلى المنفذ {port} بعد {max_retries} محاولات")
    return False

def create_app():
    """Create Flask application"""
    app = Flask(__name__, static_folder=os.path.join(project_root, 'client/dist'), static_url_path='/')

    # Enable CORS
    CORS(app, 
         supports_credentials=True,
         resources={
             r"/api/*": {
                 "origins": ["http://localhost:5000", "https://*.repl.co"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "expose_headers": ["Content-Range", "X-Content-Range"]
             }
         })

    # Import and register blueprints/routes
    from server.auth import setup_auth
    app = setup_auth(app)

    # Add root route
    @app.route('/')
    def serve_app():
        return app.send_static_file('index.html')

    # Add catch-all route for client-side routing
    @app.route('/<path:path>')
    def catch_all(path):
        return app.send_static_file('index.html')

    return app

def handle_signals():
    """إعداد معالجة الإشارات"""
    def handle_term(signum, frame):
        logger = logging.getLogger('silvarium_production')
        logger.info("تم استلام إشارة إيقاف، إغلاق التطبيق...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_term)
    signal.signal(signal.SIGINT, handle_term)

def main():
    """النقطة الرئيسية لبدء الخادم"""
    try:
        # إعداد التسجيل
        logger = setup_logging()
        logger.info("بدء تشغيل خادم Silvarium Social...")

        # إعداد معالجة الإشارات
        handle_signals()

        # تحميل المتغيرات البيئية
        load_dotenv()

        # تكوين الخادم
        host = "0.0.0.0"
        port = int(os.getenv("PORT", "5000"))

        logger.info(f"محاولة بدء الخادم على {host}:{port}")

        # انتظار حتى يصبح المنفذ متاحاً
        if not wait_for_port_available(port, max_retries=30, delay=1):
            logger.error(f"المنفذ {port} غير متاح بعد عدة محاولات")
            sys.exit(1)

        # إنشاء تطبيق Flask
        app = create_app()

        # بدء الخادم
        logger.info(f"بدء الخادم على {host}:{port}")

        # إرسال إشارة جاهزية للـ workflow
        print('ready')  # This is important for the workflow to detect the server is ready
        sys.stdout.flush()

        # تشغيل الخادم
        serve(
            app,
            host=host,
            port=port,
            threads=4,
            channel_timeout=30,
            cleanup_interval=30,
            ident='Silvarium Social'
        )

        return 0

    except Exception as e:
        logger = logging.getLogger('silvarium_production')
        logger.error(f"خطأ غير متوقع: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())