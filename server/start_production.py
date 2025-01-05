"""Main production server startup script"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from waitress import serve
import socket
import time

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup logging first
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

# Add console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Load environment variables first
load_dotenv()

# Verify required Firebase environment variables
required_env_vars = ['FIREBASE_PROJECT_ID', 'FIREBASE_PRIVATE_KEY', 'FIREBASE_CLIENT_EMAIL']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    logger.error(f"المتغيرات البيئية المطلوبة مفقودة: {', '.join(missing_vars)}")
    logger.error("Missing required environment variables")
    sys.exit(1)

# Now import the app after environment setup
from server import create_app

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 60) -> bool:
    """Wait for port availability | انتظار حتى يصبح المنفذ متاحاً"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.bind((host, port))  # Try to bind to the port
                sock.close()  # Close immediately if successful
                print(f"Port {port} is available | المنفذ {port} متاح")
                return True
        except socket.error:
            print(f"Waiting for port {port}... | انتظار المنفذ {port}...")
            time.sleep(1)

    print(f"Port {port} is not available after timeout | المنفذ {port} غير متاح بعد انتهاء المهلة")
    return False

def main():
    """Main entry point | النقطة الرئيسية لبدء الخادم"""
    try:
        # Set production mode | تعيين وضع الإنتاج
        os.environ['FLASK_ENV'] = 'production'
        os.environ['WAIT_FOR_PORT'] = 'true'

        # Get port | الحصول على المنفذ
        port = int(os.getenv('PORT', '5000'))

        # Wait for port availability | انتظار توفر المنفذ
        if not wait_for_port(port):
            logger.error(f"Port {port} is not available | المنفذ {port} غير متاح")
            return 1

        # Create Flask app | إنشاء تطبيق Flask
        app = create_app()
        if not app:
            logger.error("Failed to create Flask application | فشل في إنشاء تطبيق Flask")
            return 1

        # Signal ready | إشارة الجاهزية
        logger.info('Server is ready | الخادم جاهز')
        print('ready')
        sys.stdout.flush()

        # Start server with waitress | بدء الخادم باستخدام waitress
        serve(
            app,
            host='0.0.0.0',
            port=port,
            url_scheme='https',
            threads=4,
            channel_timeout=30,
            cleanup_interval=30,
            ident='Silvarium Social'
        )

        return 0

    except Exception as e:
        logger.error(f"Error starting server: {str(e)} | خطأ في بدء تشغيل الخادم: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())