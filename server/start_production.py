"""Main production server startup script"""
import os
import sys
import logging
from waitress import serve
from prometheus_client import start_http_server

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import from server package
from server.app import create_app, logger

def main():
    """نقطة البداية الرئيسية | Main entry point"""
    try:
        # Explicitly set production mode
        os.environ['FLASK_ENV'] = 'production'
        os.environ['PORT'] = '5000'

        logger.info("بدء تشغيل خادم سيلفاريوم الاجتماعي | Starting Silvarium Social production server")

        # Use fixed port for production
        port = 5000
        logger.info(f"تم تحديد المنفذ: {port}")

        # Start metrics server
        metrics_port = port + 1
        start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")

        # Create Flask app
        logger.info("إنشاء تطبيق Flask")
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return 1

        # Signal ready
        logger.info('الخادم جاهز | Server is ready')
        print('ready')
        sys.stdout.flush()

        # Start server with waitress
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
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())