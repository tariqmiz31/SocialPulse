"""WSGI production server configuration"""
import os
from waitress import serve
from server.start import create_app

# Create Flask application
app = create_app()

if __name__ == "__main__":
    # Get port from environment variable with fallback
    port = int(os.getenv("PORT", "8080"))

    # Configure production server
    serve(
        app,
        host="0.0.0.0",
        port=port,
        url_scheme='https',
        threads=4,
        connection_limit=1000,
        channel_timeout=30,
        cleanup_interval=30,
        ident='Silvarium Social Platform'
    )
