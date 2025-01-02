"""Initialize server package"""
from flask import Flask
from flask_cors import CORS
from flask_session import Session

app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

# تكوين CORS
CORS(app, 
     supports_credentials=True, 
     resources={
         r"/api/*": {
             "origins": ["https://*.repl.co", "https://*.repl.dev"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"]
         }
     })

# تكوين الجلسة
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

from server.config import Config, ProductionConfig, DevelopmentConfig
from server.routes import setup_routes
from server.auth import setup_auth

# إعداد المصادقة والمسارات
app = setup_auth(app)
setup_routes(app)