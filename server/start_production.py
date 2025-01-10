"""Main production server startup script"""
import os
import sys
import logging
from waitress import serve
from prometheus_client import start_http_server
import socket
import time
from flask import Flask
from flask_cors import CORS
from flask_mail import Mail
from flask_session import Session
from dotenv import load_dotenv
from datetime import timedelta

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import from server package
from server import create_app, logger

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 120) -> bool:
    """Wait for port availability"""
    start_time = time.time()
    logger.info(f"بدء انتظار المنفذ {port}...")

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                logger.info(f"المنفذ {port} متاح")
                return True
        except socket.error:
            if time.time() - start_time >= timeout:
                logger.error(f"المنفذ {port} غير متاح بعد {timeout} ثانية")
                return False
            time.sleep(1)
            logger.info(f"انتظار المنفذ {port}...")

def main():
    """نقطة البداية الرئيسية | Main entry point"""
    try:
        # Explicitly set production mode
        os.environ['FLASK_ENV'] = 'production'
        os.environ['WAIT_FOR_PORT'] = 'true'  # Enable port waiting

        # Load environment variables
        load_dotenv()

        logger.info("بدء تشغيل خادم سيلفاريوم الاجتماعي | Starting Silvarium Social production server")

        # Use fixed port for production
        port = 5000
        logger.info(f"تم تحديد المنفذ: {port}")

        # Wait for port availability
        if not wait_for_port(port):
            logger.error(f"المنفذ {port} غير متاح بعد {120} ثانية")
            return 1

        # Start metrics server
        metrics_port = port + 1
        start_http_server(metrics_port)
        logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port}")

        # Create Flask app with proper configuration
        logger.info("إنشاء تطبيق Flask")
        app = create_app()
        if not app:
            logger.error("فشل في إنشاء تطبيق Flask")
            return 1

        # Set up session configuration
        app.config.update(
            SESSION_TYPE='filesystem',
            SESSION_PERMANENT=True,
            PERMANENT_SESSION_LIFETIME=timedelta(days=1),
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            SESSION_FILE_DIR='/tmp/flask_session',
            SESSION_FILE_THRESHOLD=500,
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            WAIT_FOR_PORT=True,  # Enable port waiting
            WAIT_FOR_PORT_TIMEOUT=120  # Set timeout to 2 minutes
        )

        # Initialize session
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])
        Session(app)

        # Signal ready to workflow
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
            ident='Silvarium Social',
            clear_untrusted_proxy_headers=True,
            trusted_proxy_headers=['x-forwarded-for', 'x-forwarded-proto'],
            trusted_proxy='127.0.0.1'
        )

        return 0

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())