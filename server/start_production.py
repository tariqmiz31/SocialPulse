import os
import sys
from dotenv import load_dotenv
from server.wsgi import app
from waitress import serve

def main():
    # Load environment variables
    load_dotenv()
    
    # Validate required environment variables
    required_vars = ['APP_URL', 'ALLOWED_ORIGINS', 'SECRET_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Get port from environment variable with fallback
    port = int(os.getenv("PORT", "5000"))
    
    print(f"Starting production server on port {port}")
    print(f"Main domain: {os.getenv('APP_URL')}")
    print(f"Allowed origins: {os.getenv('ALLOWED_ORIGINS')}")
    
    # Start production server
    serve(
        app,
        host="0.0.0.0",
        port=port,
        url_scheme='https',
        threads=4,
        connection_limit=1000,
        channel_timeout=30
    )

if __name__ == "__main__":
    main()
