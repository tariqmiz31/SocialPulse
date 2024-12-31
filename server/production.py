import os
import sys
from flask import Flask
from waitress import serve
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('socialpulse')
handler = RotatingFileHandler('socialpulse.log', maxBytes=10000, backupCount=3)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)

def create_app():
    # Import app after environment variables are loaded
    try:
        from server.index import app
        return app
    except Exception as e:
        logger.error(f"Failed to create app: {e}")
        sys.exit(1)

def main():
    # Validate environment variables
    required_vars = ['APP_URL', 'ALLOWED_ORIGINS', 'SECRET_KEY', 'DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    app = create_app()
    port = int(os.getenv("PORT", "5000"))
    
    logger.info(f"Starting production server on port {port}")
    logger.info(f"Main domain: {os.getenv('APP_URL')}")
    logger.info(f"Allowed origins: {os.getenv('ALLOWED_ORIGINS')}")
    
    try:
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
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
