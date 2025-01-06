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
from server import create_app, DEFAULT_PORT, WAIT_FOR_PORT_TIMEOUT

# Setup logging first
logger = logging.getLogger('silvarium_production')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

if not os.path.exists('/tmp/logs'):
    os.makedirs('/tmp/logs')

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

def check_firebase_prerequisites() -> bool:
    """Check if all Firebase prerequisites are met"""
    try:
        service_account_path = 'attached_assets/silva-deb1c-firebase-adminsdk-g19p8-5d6dc42cd6.json'

        if not os.path.exists(service_account_path):
            logger.error(f"Service account file not found at: {service_account_path}")
            return False

        try:
            with open(service_account_path, 'r') as file:
                cred_dict = json.load(file)
                logger.info("Successfully loaded service account file")

                # Set environment variables
                os.environ['FIREBASE_PROJECT_ID'] = cred_dict['project_id']
                os.environ['FIREBASE_PRIVATE_KEY'] = cred_dict['private_key']
                os.environ['FIREBASE_CLIENT_EMAIL'] = cred_dict['client_email']

                return True

        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error reading service account file: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"Error checking Firebase prerequisites: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = WAIT_FOR_PORT_TIMEOUT) -> bool:
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
        # Set production environment and enable port waiting
        os.environ['FLASK_ENV'] = 'production'
        os.environ['WAIT_FOR_PORT'] = 'true'

        logger.info("Starting Silvarium Social production server")

        # Check Firebase prerequisites first
        logger.info("Checking Firebase prerequisites...")
        if not check_firebase_prerequisites():
            logger.error("Failed to meet Firebase prerequisites - exiting")
            return 1

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