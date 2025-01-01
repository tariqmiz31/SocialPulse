import os
import sys
import socket
from dotenv import load_dotenv
from waitress import serve
from flask import Flask
from flask_cors import CORS
from werkzeug.security import generate_password_hash
import psycopg2
import logging
from logging.handlers import RotatingFileHandler
from prometheus_client import start_http_server

# Create Flask app
app = Flask(__name__)
CORS(app)

# تكوين التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

def setup_logging():
    log_dir = '/tmp/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    file_handler = RotatingFileHandler(
        f'{log_dir}/silvarium.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    logger.addHandler(file_handler)

def create_admin_user():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # Check if admin exists
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if cur.fetchone() is None:
            # Create admin user with hashed password
            hashed_password = generate_password_hash('admin123')
            cur.execute(
                """
                INSERT INTO users (username, password, role, is_approved, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ('admin', hashed_password, 'admin', True, 'active')
            )
            conn.commit()
            logger.info("Admin user created successfully")

        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")

def main():
    # Load environment variables
    load_dotenv()

    # Setup logging
    setup_logging()

    # Start metrics server
    metrics_port = int(os.getenv('METRICS_PORT', '9090'))
    while is_port_in_use(metrics_port):
        logger.warning(f"Port {metrics_port} is in use, trying next port")
        metrics_port += 1

    try:
        start_http_server(metrics_port)
        logger.info(f"Metrics server started on port {metrics_port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")

    # Validate required environment variables
    required_vars = ['DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    # Configure app
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

    # Create admin user
    create_admin_user()

    # Get port from environment variable with fallback
    port = int(os.getenv("PORT", "5000"))

    # Check if port is in use and find next available port
    while is_port_in_use(port):
        logger.warning(f"Port {port} is in use, trying next port")
        port += 1

    logger.info(f"Starting production server on port {port}")
    logger.info(f"Database URL configured: {bool(app.config['SQLALCHEMY_DATABASE_URI'])}")

    try:
        # Start production server with waitress
        serve(
            app,
            host="0.0.0.0",
            port=port,
            url_scheme='https',
            threads=4,
            connection_limit=1000,
            channel_timeout=30
        )
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()