"""Initialize server package"""
from flask import Flask
from flask_cors import CORS

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

from server.config import Config, ProductionConfig, DevelopmentConfig
from server.routes import setup_routes

# Setup routes
setup_routes(app)