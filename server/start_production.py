import os
import sys
from dotenv import load_dotenv
from waitress import serve
from flask import Flask
from flask_cors import CORS

# Create Flask app
app = Flask(__name__)
CORS(app)

def main():
    # Load environment variables
    load_dotenv()

    # Validate required environment variables
    required_vars = ['APP_URL', 'ALLOWED_ORIGINS', 'SECRET_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    # Configure app from environment
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

    # Get port from environment variable with fallback
    port = int(os.getenv("PORT", "5000"))

    print(f"Starting production server on port {port}")
    print(f"Main domain: {os.getenv('APP_URL')}")
    print(f"Allowed origins: {os.getenv('ALLOWED_ORIGINS')}")
    print(f"Database URL configured: {bool(app.config['SQLALCHEMY_DATABASE_URI'])}")

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
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()