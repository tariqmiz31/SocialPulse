"""Production server configuration"""
import os
import logging
from logging.handlers import RotatingFileHandler

# تكوين السجلات
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# إعداد ملف السجلات الدوار
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, 'production.log'),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    '%Y-%m-%d %H:%M:%S'
))

# تكوين الخادم
PRODUCTION_CONFIG = {
    'host': '0.0.0.0',
    'port': int(os.getenv('PORT', '5000')),
    'threads': 4,
    'url_scheme': 'https',
    'connection_limit': 1000,
    'cleanup_interval': 30,
    'channel_timeout': 30,
    'log_untrusted_proxy_headers': True,
    'trusted_proxy': '*',
    'log_socket_errors': True,
    'wait_for_port': True,  # تمكين انتظار المنفذ
    'wait_for_port_timeout': 60,  # مدة الانتظار بالثواني
    'port_cleanup_attempts': 5,  # عدد محاولات تنظيف المنفذ
    'port_cleanup_interval': 2,  # الفاصل الزمني بين محاولات التنظيف بالثواني
}

# تكوين التطبيق
APP_CONFIG = {
    'SESSION_COOKIE_SECURE': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'PERMANENT_SESSION_LIFETIME': 86400,  # 24 ساعة
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    'JSON_AS_ASCII': False,
    'JSON_SORT_KEYS': False,
    'PROPAGATE_EXCEPTIONS': True,
    'PRESERVE_CONTEXT_ON_EXCEPTION': True,
}