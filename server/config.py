import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """التكوين الأساسي للتطبيق"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'silvarium-social-default-key')
    DATABASE_URL = os.getenv('DATABASE_URL')
    DEBUG = False
    PORT = int(os.getenv('PORT', 5001))  # تغيير المنفذ الافتراضي إلى 5001
    HOST = '0.0.0.0'

    # إعدادات الجلسة
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = '/tmp/flask_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 دقيقة

class ProductionConfig(Config):
    """تكوين بيئة الإنتاج"""
    ENV = 'production'
    DEBUG = False
    SESSION_COOKIE_SECURE = True

class DevelopmentConfig(Config):
    """تكوين بيئة التطوير"""
    ENV = 'development'
    DEBUG = True
    SESSION_COOKIE_SECURE = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}