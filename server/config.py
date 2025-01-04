"""Application Configuration Module"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """التكوين الأساسي للتطبيق | Base Application Configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'silvarium-social-default-key')
    DATABASE_URL = os.getenv('DATABASE_URL')
    DEBUG = False
    PORT = int(os.getenv('PORT', '8080'))  # Using port 8080 as default
    HOST = '0.0.0.0'

    # إعدادات الجلسة | Session Settings
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = '/tmp/flask_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes | 30 دقيقة

    # إعدادات Firebase | Firebase Settings
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
    FIREBASE_PRIVATE_KEY = os.getenv('FIREBASE_PRIVATE_KEY')
    FIREBASE_CLIENT_EMAIL = os.getenv('FIREBASE_CLIENT_EMAIL')

    # إعدادات انتظار المنفذ | Port Waiting Settings
    WAIT_FOR_PORT = True  # Always wait for port in all environments
    WAIT_FOR_PORT_TIMEOUT = 60  # Increased timeout to ensure server readiness

    # إعدادات اللغة | Language Settings
    DEFAULT_LANGUAGE = 'ar'  # Arabic as default language
    SUPPORTED_LANGUAGES = ['ar', 'en']

class ProductionConfig(Config):
    """تكوين بيئة الإنتاج | Production Environment Configuration"""
    ENV = 'production'
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    CORS_ORIGINS = [
        'https://*.repl.co',
        'https://*.repl.dev',
        os.getenv('APP_URL', 'https://silvariumsocial.com')
    ]

class DevelopmentConfig(Config):
    """تكوين بيئة التطوير | Development Environment Configuration"""
    ENV = 'development'
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    CORS_ORIGINS = [
        'http://localhost:8080',
        'https://localhost:8080'
    ]

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}