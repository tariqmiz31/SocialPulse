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

from server import create_app

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 60) -> bool:
    """Wait for port availability | انتظار حتى يصبح المنفذ متاحاً"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result != 0:  # Port is available
                    print(f"Port {port} is available | المنفذ {port} متاح")
                    return True
                print(f"Waiting for port {port}... | انتظار المنفذ {port}...")
                time.sleep(1)
        except Exception as e:
            print(f"Error checking port {port}: {str(e)} | خطأ في فحص المنفذ {port}: {str(e)}")
            return False

    print(f"Port {port} is not available after timeout | المنفذ {port} غير متاح بعد انتهاء المهلة")
    return False

def main():
    """Main entry point | النقطة الرئيسية لبدء الخادم"""
    try:
        # Set production mode | تعيين وضع الإنتاج
        os.environ['FLASK_ENV'] = 'production'

        # Load environment variables | تحميل المتغيرات البيئية
        load_dotenv()

        # Create Flask app | إنشاء تطبيق Flask
        app = create_app()
        if not app:
            print("Failed to create Flask application | فشل في إنشاء تطبيق Flask", file=sys.stderr)
            return 1

        # Get port | الحصول على المنفذ
        port = int(os.getenv('PORT', '8080'))

        # Wait for port availability | انتظار توفر المنفذ
        if not wait_for_port(port):
            print(f"Port {port} is not available | المنفذ {port} غير متاح", file=sys.stderr)
            return 1

        # Signal ready before starting server | إشارة الجاهزية قبل بدء الخادم
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
        print(f"Unexpected error: {str(e)} | خطأ غير متوقع: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())