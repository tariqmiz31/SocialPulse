"""Main production server startup script"""
import os
import sys
import logging
import traceback
from logging.handlers import RotatingFileHandler
from waitress import serve
import socket
import time
import json
import firebase_admin
from firebase_admin import credentials, auth

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import from server package
from server import create_app

# Setup logging first
logger = logging.getLogger('silvarium_production')
logger.setLevel(logging.INFO)

# Ensure logs directory exists
if not os.path.exists('/tmp/logs'):
    os.makedirs('/tmp/logs')

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

file_handler = RotatingFileHandler(
    '/tmp/logs/silvarium.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 30) -> bool:
    """Wait for port availability"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                sock.close()
                logger.info(f"Port {port} is available")
                return True
        except socket.error:
            logger.info(f"Waiting for port {port}...")
            time.sleep(1)

    logger.error(f"Port {port} is not available after {timeout} seconds")
    return False

def main():
    """Main entry point"""
    try:
        # Set production environment
        os.environ['FLASK_ENV'] = 'production'
        os.environ['WAIT_FOR_PORT'] = 'true'

        logger.info("Starting Silvarium Social production server")


        # Use configured port or default to 5000
        try:
            port = int(os.getenv('PORT', '5000'))
        except ValueError:
            logger.warning("Invalid PORT environment variable, using default port 5000")
            port = 5000

        # Wait for port availability
        if not wait_for_port(port):
            logger.error(f"Port {port} is not available - exiting")
            return 1

        # Create Flask app
        logger.info("Creating Flask application")
        app = create_app()
        if not app:
            logger.error("Failed to create Flask application")
            return 1

        # Signal ready
        logger.info('Server is ready')
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
        logger.error(f"Error starting server: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())