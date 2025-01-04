import os
import sys
from waitress import serve
import logging
from logging.handlers import RotatingFileHandler
import socket
import time
from dotenv import load_dotenv
import signal
import prometheus_client

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Import after adding project root to path
from server import create_app
from server.config import config

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
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', port))
                sock.close()
                logger.info(f"المنفذ {port} متاح للاستخدام | Port {port} is available")
                return True
        except socket.error:
            if i < max_retries - 1:
                logger.warning(f"المنفذ {port} مشغول، محاولة {i+1}/{max_retries}. انتظار {delay} ثوانٍ... | Port {port} is busy, attempt {i+1}/{max_retries}. Waiting {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"فشل في الوصول إلى المنفذ {port} بعد {max_retries} محاولات | Failed to access port {port} after {max_retries} attempts")
                return False

    return False

def handle_signals(server=None):
    """إعداد معالجة الإشارات"""
    def handle_term(signum, frame):
        logger = logging.getLogger('silvarium_production')
        logger.info("تم استلام إشارة إيقاف، إغلاق التطبيق... | Received termination signal, shutting down...")
        if server:
            server.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_term)
    signal.signal(signal.SIGINT, handle_term)

def main():
    """النقطة الرئيسية لبدء الخادم"""
    try:
        # إعداد التسجيل
        logger = setup_logging()
        logger.info("بدء تشغيل خادم Silvarium Social... | Starting Silvarium Social server...")

        # تحميل المتغيرات البيئية والتكوين
        load_dotenv()
        env = os.getenv('FLASK_ENV', 'production')
        app_config = config[env]

        # تكوين الخادم
        host = '0.0.0.0'
        port = int(os.getenv('PORT', '8080'))

        logger.info(f"محاولة بدء الخادم على {host}:{port} | Attempting to start server on {host}:{port}")

        # انتظار حتى يصبح المنفذ متاحاً
        if not wait_for_port_available(port):
            logger.error(f"المنفذ {port} غير متاح | Port {port} is not available")
            return 1

        # إنشاء تطبيق Flask
        app = create_app()

        # بدء خادم المقاييس على منفذ مختلف
        metrics_port = port + 1
        prometheus_client.start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port} | Metrics server started on port {metrics_port}")

        # إعداد معالجة الإشارات
        handle_signals()

        # تشغيل الخادم
        server = serve(
            app,
            host=host,
            port=port,
            url_scheme='https',
            threads=4,
            channel_timeout=30,
            cleanup_interval=30,
            ident='Silvarium Social'
        )

        # إرسال إشارة جاهزية
        print('ready')
        sys.stdout.flush()

        return 0

    except Exception as e:
        logger = logging.getLogger('silvarium_production')
        logger.error(f"خطأ غير متوقع: {str(e)} | Unexpected error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())