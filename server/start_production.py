import os
import sys
import socket
import time
from dotenv import load_dotenv
from waitress import serve
from flask import Flask
from flask_cors import CORS
from werkzeug.security import generate_password_hash
import psycopg2
import logging
from logging.handlers import RotatingFileHandler

# Create Flask app
app = Flask(__name__)
CORS(app)

# تكوين التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

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
        raise

def main():
    try:
        # Load environment variables
        load_dotenv()

        # Setup logging
        setup_logging()

        # Validate required environment variables
        if not os.getenv('DATABASE_URL'):
            logger.error("Missing DATABASE_URL environment variable")
            sys.exit(1)

        # Configure app
        app.config.update(
            SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL'),
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24)),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            PERMANENT_SESSION_LIFETIME=1800  # 30 minutes
        )

        # Create admin user
        create_admin_user()

        port = int(os.getenv("PORT", "5001"))

        logger.info(f"Starting production server on port {port}")
        logger.info(f"Database URL configured: {bool(app.config['SQLALCHEMY_DATABASE_URI'])}")

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

        return True
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        raise

if __name__ == "__main__":
    main()