import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'silvarium-social-default-key')
    DATABASE_URL = os.getenv('DATABASE_URL')
    DEBUG = False
    PORT = int(os.getenv('PORT', 5000))
    HOST = '0.0.0.0'

class ProductionConfig(Config):
    ENV = 'production'
    DEBUG = False

class DevelopmentConfig(Config):
    ENV = 'development'
    DEBUG = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
