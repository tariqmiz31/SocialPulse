from server.index import app
from waitress import serve
import os

if __name__ == "__main__":
    # Get port from environment variable with fallback
    port = int(os.getenv("PORT", "5000"))
    
    # Configure production server
    serve(
        app,
        host="0.0.0.0",
        port=port,
        url_scheme='https',
        threads=4,
        connection_limit=1000,
        channel_timeout=30
    )
