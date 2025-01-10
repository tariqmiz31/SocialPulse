from flask import Flask, send_from_directory, jsonify, request
import os
from flask_mail import Message, Mail
from functools import wraps
import secrets
import datetime
import logging

# Initialize Flask-Mail and logger
mail = Mail()
logger = logging.getLogger('silvarium')

def login_required(f):
    """تأكد من تسجيل دخول المستخدم"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            return jsonify({'message': 'يجب تسجيل الدخول'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """تأكد من أن المستخدم مشرف"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            return jsonify({'message': 'يجب تسجيل الدخول'}), 401
        if request.user.role != 'admin':
            return jsonify({'message': 'غير مصرح بهذا الإجراء'}), 403
        return f(*args, **kwargs)
    return decorated_function

def register_routes(app: Flask) -> Flask:
    """تسجيل مسارات التطبيق"""
    # تهيئة خدمة البريد الإلكتروني
    mail.init_app(app)

    # المسار الرئيسي وخدمة الملفات الثابتة
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        """خدمة الملفات الثابتة للتطبيق"""
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    return app