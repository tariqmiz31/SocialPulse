"""Initialize server package"""
import os
from flask import Flask
from flask_cors import CORS
from flask_session import Session
from datetime import timedelta

app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

# تكوين CORS
CORS(app, 
     supports_credentials=True, 
     resources={
         r"/api/*": {
             "origins": ["*"],  # السماح بجميع المصادر في بيئة التطوير
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Content-Range", "X-Content-Range"],
             "supports_credentials": True
         }
     })

# تكوين الجلسة
app.config.update(
    SESSION_TYPE='filesystem',
    SESSION_COOKIE_SECURE=False,  # تعطيل في بيئة التطوير
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=1),  # زيادة مدة الجلسة
    SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex())
)
Session(app)

from server.config import Config, ProductionConfig, DevelopmentConfig
from server.routes import setup_routes
from server.auth import setup_auth

# إعداد المصادقة والمسارات
app = setup_auth(app)
app = setup_routes(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)