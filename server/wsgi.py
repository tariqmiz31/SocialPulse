"""WSGI production server configuration"""
import os
import logging
from waitress import serve
from prometheus_client import start_http_server
from server.start import create_app, setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger('silvarium')

# Create Flask application
app = create_app()

if __name__ == "__main__":
    try:
        # Get port from environment variable with fallback
        port = int(os.getenv("PORT", "8080"))

        # Start metrics server
        metrics_port = port + 1
        start_http_server(metrics_port)
        logger.info(f"Started metrics server on port {metrics_port}")

        # Configure production server
        logger.info(f"Starting production server on port {port}")
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
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        raise