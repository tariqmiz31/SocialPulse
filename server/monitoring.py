import os
from prometheus_client import Counter, Histogram, start_http_server
import logging
from logging.handlers import RotatingFileHandler
import time
from functools import wraps
from typing import Callable
from flask import request, Response
import psycopg2

# تكوين التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

# إعداد تسجيل الملفات
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

# مقاييس Prometheus
REQUEST_COUNT = Counter(
    'silvarium_request_count',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'silvarium_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

ERROR_COUNT = Counter(
    'silvarium_error_count',
    'Total number of errors',
    ['type']
)

DB_QUERY_LATENCY = Histogram(
    'silvarium_db_query_latency_seconds',
    'Database query latency in seconds',
    ['query_type']
)

def setup_monitoring(app, metrics_port=9090):
    """إعداد المراقبة للتطبيق"""
    # بدء خادم مقاييس Prometheus
    start_http_server(metrics_port)
    logger.info(f'تم بدء خادم المقاييس على المنفذ {metrics_port}')

    # إضافة التسجيل لكل الطلبات
    @app.before_request
    def before_request():
        request.start_time = time.time()

    @app.after_request
    def after_request(response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown',
                status=response.status_code
            ).inc()

            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown'
            ).observe(duration)

            if response.status_code >= 400:
                ERROR_COUNT.labels(type=str(response.status_code)).inc()

        return response

    # نقطة نهاية لفحص الصحة
    @app.route('/api/monitoring/health')
    def health_check():
        try:
            # فحص اتصال قاعدة البيانات
            start_time = time.time()
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            duration = time.time() - start_time
            DB_QUERY_LATENCY.labels(query_type='connection').observe(duration)

            conn.close()
            return {
                'status': 'healthy',
                'database': 'connected',
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f'فشل فحص الصحة: {str(e)}')
            return {
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': str(e)
            }, 500

    return app

def monitor_performance(func: Callable) -> Callable:
    """مراقب أداء نقاط النهاية"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            response = func(*args, **kwargs)
            status = response.status_code if isinstance(response, Response) else 200
        except Exception as e:
            logger.error(f'خطأ في {func.__name__}: {str(e)}')
            ERROR_COUNT.labels(type=type(e).__name__).inc()
            raise

        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=status
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.path
        ).observe(duration)

        return response
    return wrapper

def log_error(error: Exception, context: dict = None):
    """تسجيل الأخطاء مع السياق"""
    error_details = {
        'type': type(error).__name__,
        'message': str(error),
        'context': context or {}
    }
    logger.error(f'Application error: {error_details}')
    ERROR_COUNT.labels(type=type(error).__name__).inc()

def get_health_data():
    """الحصول على بيانات صحة التطبيق"""
    try:
        return {
            'status': 'healthy',
            'timestamp': time.time(),
            'version': os.getenv('APP_VERSION', '1.0.0'),
            'environment': os.getenv('FLASK_ENV', 'production')
        }
    except Exception as e:
        log_error(e)
        return {
            'status': 'unhealthy',
            'error': str(e)
        }