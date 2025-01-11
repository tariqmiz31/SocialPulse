from flask import Flask, send_from_directory, jsonify, request
import os
from flask_mail import Message, Mail
from functools import wraps
import secrets
import datetime
import logging
from flask_cors import CORS

# Initialize Flask-Mail and logger
mail = Mail()
logger = logging.getLogger('silvarium')

def register_routes(app: Flask) -> Flask:
    """تسجيل مسارات التطبيق"""

    # تهيئة خدمة البريد الإلكتروني
    mail.init_app(app)

    # تكوين CORS للمسارات
    CORS(app, 
         supports_credentials=True,
         resources={
             r"/api/*": {
                 "origins": ["http://localhost:5000", "https://*.repl.co", "http://0.0.0.0:5000"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "expose_headers": ["Content-Type"],
                 "supports_credentials": True
             }
         })

    @app.before_request
    def handle_preflight():
        """معالجة طلبات CORS المسبقة"""
        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            return response

    # المسار الرئيسي وخدمة الملفات الثابتة
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        """خدمة الملفات الثابتة للتطبيق"""
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    return app