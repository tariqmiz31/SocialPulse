"""Production Server Configuration"""
import os
import sys
import time
import socket
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS
from waitress import serve
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

def setup_logging():
    """Sets up logging with rotation"""
    log_dir = '/tmp/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger('silvarium_production')
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    )

    file_handler = RotatingFileHandler(
        f'{log_dir}/silvarium.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 60) -> bool:
    """انتظار حتى يصبح المنفذ متاحاً | Wait until port becomes available"""
    start_time = time.time()
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Instead of binding, try to connect to check if port is in use
                result = sock.connect_ex((host, port))
                if result != 0:  # Port is available
                    logger.info(f"Port {port} is available")
                    return True
                else:  # Port is in use
                    if time.time() - start_time >= timeout:
                        logger.error(f"Port {port} is not available after {timeout} seconds")
                        return False
                    logger.info(f"Waiting for port {port} to become available...")
                    time.sleep(1)
        except Exception as e:
            logger.error(f"Error checking port {port}: {str(e)}")
            return False

def init_firebase() -> bool:
    """تهيئة Firebase | Initialize Firebase"""
    try:
        service_account_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'attached_assets',
            'silva-11e9d-firebase-adminsdk-n8a88-74bc434752.json'
        )

        if not os.path.exists(service_account_path):
            logger.error("Firebase service account file not found")
            return False

        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully")

        return True
    except Exception as e:
        logger.error(f"Firebase initialization error: {str(e)}")
        return False

def main() -> bool:
    """Main entry point"""
    try:
        # Set FLASK_ENV to production
        os.environ['FLASK_ENV'] = 'production'

        load_dotenv()
        logger.info("Starting Silvarium Social server")

        # Check for required environment variables
        if not os.getenv('DATABASE_URL'):
            logger.error("DATABASE_URL not found")
            return False

        # Initialize Firebase for SMS verification
        if not init_firebase():
            logger.error("Failed to initialize Firebase")
            return False

        # Create Flask app with production config
        from server import create_app
        app = create_app()
        if not app:
            logger.error("Failed to create Flask application")
            return False

        port = int(os.getenv("PORT", "8080"))

        # Always wait for port in production
        if not wait_for_port(port, timeout=60):
            logger.error(f"Port {port} is not available after timeout")
            return False

        # Signal that we're ready to accept connections
        print("ready")
        sys.stdout.flush()

        logger.info(f"Starting server on port {port}")

        # Start the production server with waitress
        serve(
            app,
            host="0.0.0.0",
            port=port,
            url_scheme='https',
            threads=4,
            channel_timeout=30,
            cleanup_interval=30,
            ident='Silvarium Social'
        )

        return True

    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)