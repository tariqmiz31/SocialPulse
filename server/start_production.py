"""Main production server startup script"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from waitress import serve

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server import create_app

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

        # Signal ready before starting server | إشارة الجاهزية قبل بدء الخادم
        print('ready')
        sys.stdout.flush()

        # Start server with waitress | بدء الخادم باستخدام waitress
        port = app.config['PORT']
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