"""Production Server Configuration"""
import os
import sys
import time
import socket
import logging
import json
import traceback
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS
from waitress import serve
import firebase_admin
from firebase_admin import credentials

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup logging
logger = logging.getLogger('silvarium_production')
logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
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

def check_firebase_prerequisites() -> bool:
    """Check if all Firebase prerequisites are met"""
    try:
        service_account_path = 'attached_assets/silva-deb1c-firebase-adminsdk-g19p8-5d6dc42cd6.json'

        # Check file existence and permissions
        if not os.path.exists(service_account_path):
            logger.error(f"Service account file not found at: {service_account_path}")
            logger.error(f"Current directory files: {os.listdir('.')}")
            logger.error(f"Attached assets files: {os.listdir('attached_assets')}")
            return False

        # Verify file readability and content
        try:
            with open(service_account_path, 'r') as file:
                content = file.read()
                logger.info("Successfully read service account file")

            # Verify JSON parsing
            try:
                cred_dict = json.loads(content)
                logger.info("Successfully parsed service account JSON")

                # Check required fields
                required_fields = ['project_id', 'private_key', 'client_email']
                for field in required_fields:
                    if field not in cred_dict:
                        logger.error(f"Missing required field in service account JSON: {field}")
                        return False
                    logger.info(f"Found required field: {field}")

                return True

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in service account file: {str(e)}")
                return False

        except IOError as e:
            logger.error(f"Cannot read service account file: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"Error checking Firebase prerequisites: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def init_firebase() -> bool:
    """Initialize Firebase with detailed error handling"""
    if not check_firebase_prerequisites():
        logger.error("Firebase prerequisites check failed")
        return False

    try:
        service_account_path = 'attached_assets/silva-deb1c-firebase-adminsdk-g19p8-5d6dc42cd6.json'
        with open(service_account_path, 'r') as file:
            cred_dict = json.load(file)

        # Set environment variables
        os.environ['FIREBASE_PROJECT_ID'] = cred_dict['project_id']
        os.environ['FIREBASE_PRIVATE_KEY'] = cred_dict['private_key']
        os.environ['FIREBASE_CLIENT_EMAIL'] = cred_dict['client_email']

        logger.info("Successfully set Firebase environment variables")

        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred, {
                'auth_settings': {
                    'sms_verification_message': 'يرجى استخدام الرقم المؤقت لاستعادة كلمة المرور: %CODE%',
                    'code_length': 4
                }
            })
            logger.info("Firebase Admin SDK initialized successfully")
        else:
            logger.info("Firebase Admin SDK already initialized")

        return True

    except Exception as e:
        logger.error(f"Firebase initialization error: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def wait_for_port(port: int, host: str = '0.0.0.0', timeout: int = 30) -> bool:
    """Wait until port becomes available"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                sock.close()
                logger.info(f"Port {port} is available")
                return True
        except socket.error:
            time.sleep(1)
            logger.info(f"Waiting for port {port}...")

    logger.error(f"Port {port} is not available after {timeout} seconds")
    return False

def main() -> int:
    """Main entry point"""
    try:
        # Set production environment
        os.environ['FLASK_ENV'] = 'production'

        logger.info("Starting Silvarium Social production server")

        # First check and initialize Firebase
        logger.info("Checking Firebase prerequisites...")
        if not check_firebase_prerequisites():
            logger.error("Failed to meet Firebase prerequisites - exiting")
            return 1

        logger.info("Initializing Firebase...")
        if not init_firebase():
            logger.error("Failed to initialize Firebase - exiting")
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
        from server import create_app
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