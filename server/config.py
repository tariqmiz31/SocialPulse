"""Application Configuration Module"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """التكوين الأساسي للتطبيق | Base Application Configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'silvarium-social-default-key')
    DATABASE_URL = os.getenv('DATABASE_URL')
    DEBUG = False
    PORT = int(os.getenv('PORT', '5000'))
    HOST = '0.0.0.0'

    # إعدادات الجلسة | Session Settings
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = '/tmp/flask_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes | 30 دقيقة

    # إعدادات انتظار المنفذ | Port Waiting Settings
    WAIT_FOR_PORT = True
    WAIT_FOR_PORT_TIMEOUT = 120

    # إعدادات التحقق عبر البريد الإلكتروني | Email Verification Settings
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@silvariumsocial.com')
    EMAIL_CODE_LENGTH = 4
    EMAIL_CODE_EXPIRY = 600  # 10 minutes
    EMAIL_MAX_ATTEMPTS = 5

    # إعدادات اللغة | Language Settings
    DEFAULT_LANGUAGE = 'ar'
    SUPPORTED_LANGUAGES = ['ar', 'en']

class ProductionConfig(Config):
    """تكوين بيئة الإنتاج | Production Environment Configuration"""
    ENV = 'production'
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    CORS_ORIGINS = [
        'https://*.repl.co',
        'https://*.repl.dev',
        'http://localhost:5000',
        'https://localhost:5000',
        os.getenv('APP_URL', 'https://silvariumsocial.com')
    ]
    WAIT_FOR_PORT = True
    WAIT_FOR_PORT_TIMEOUT = 120

class DevelopmentConfig(Config):
    """تكوين بيئة التطوير | Development Environment Configuration"""
    ENV = 'development'
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    CORS_ORIGINS = [
        'http://localhost:5000',
        'https://localhost:5000'
    ]
    WAIT_FOR_PORT = True
    WAIT_FOR_PORT_TIMEOUT = 120

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}