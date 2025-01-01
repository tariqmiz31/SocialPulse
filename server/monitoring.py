import os
from prometheus_client import Counter, Histogram, start_http_server
import logging
from logging.handlers import RotatingFileHandler
import time
from functools import wraps
from typing import Callable
from flask import request, Response

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
    'request_count',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

ERROR_COUNT = Counter(
    'error_count',
    'Total number of errors',
    ['type']
)

def start_metrics_server():
    """بدء خادم مقاييس Prometheus"""
    metrics_port = int(os.getenv('METRICS_PORT', '9090'))
    start_http_server(metrics_port)
    logger.info(f'Metrics server started on port {metrics_port}')

def monitor_performance(func: Callable) -> Callable:
    """مراقب أداء نقاط النهاية"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            response = func(*args, **kwargs)
            status = response.status_code if isinstance(response, Response) else 200
        except Exception as e:
            logger.error(f'Error in {func.__name__}: {str(e)}')
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
