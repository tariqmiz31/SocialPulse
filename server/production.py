"""تكوين خادم الإنتاج | Production Server Configuration"""
import os
import sys
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import prometheus_client
from prometheus_client import Counter, Histogram
from waitress import serve

# Application setup
app = Flask(__name__, static_folder='../client/dist', static_url_path='/')
CORS(app, 
     supports_credentials=True, 
     resources={
         r"/api/*": {
             "origins": ["https://*.repl.co", "https://*.repl.dev"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"]
         }
     })

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

def setup_logging():
    """Sets up logging with rotation"""
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

# Prometheus metrics
REQUEST_COUNT = Counter('request_count', 'Total number of requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency in seconds', ['method', 'endpoint'])

@app.before_request
def before_request():
    """Record request start time"""
    request.start_time = prometheus_client.time.time()

@app.after_request
def after_request(response):
    """Record request metrics"""
    if hasattr(request, 'start_time'):
        duration = prometheus_client.time.time() - request.start_time
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.path
        ).observe(duration)

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.path,
        status=response.status_code
    ).inc()

    return response

# Serve static files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


def main():
    """Main entry point"""
    try:
        # Load environment variables
        load_dotenv()

        # Setup logging
        setup_logging()
        logger.info("تم بدء خادم Silvarium Social | Starting Silvarium Social server")

        # Check for required environment variables
        if not os.getenv('DATABASE_URL'):
            logger.error("DATABASE_URL غير موجود | DATABASE_URL not found")
            sys.exit(1)

        # Configure the app
        app.config.update(
            SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL'),
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24)),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes
        )

        port = int(os.getenv("PORT", "8080"))
        logger.info(f"بدء الخادم على المنفذ {port} | Starting server on port {port}")

        # Start the metrics server
        metrics_port = port + 1
        try:
            prometheus_client.start_http_server(metrics_port)
            logger.info(f"تم بدء خادم المقاييس على المنفذ {metrics_port} | Metrics server started on port {metrics_port}")
        except Exception as e:
            logger.warning(f"فشل في بدء خادم المقاييس: {str(e)} | Failed to start metrics server: {str(e)}")

        # Start the production server with waitress
        serve(
            app,
            host="0.0.0.0",
            port=port,
            url_scheme='https',
            threads=4,
            connection_limit=1000,
            channel_timeout=30,
            _quiet=True  # Reduce waitress logs
        )

        # Signal that the server is ready
        print("ready")
        sys.stdout.flush()

        return True
    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {str(e)} | Error starting server: {str(e)}")
        raise

if __name__ == "__main__":
    sys.exit(0 if main() else 1)