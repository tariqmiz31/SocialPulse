from flask import Flask, send_from_directory, jsonify, request
import os
from server.blueprints.auth import auth_bp, init_auth

def setup_routes(app: Flask):
    """إعداد مسارات التطبيق"""

    # تسجيل مسارات المصادقة
    app.register_blueprint(auth_bp)

    # المسار الرئيسي وخدمة الملفات الثابتة
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        """خدمة الملفات الثابتة للتطبيق"""
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    # معالجة الأخطاء
    @app.errorhandler(404)
    def not_found_error(error):
        """معالجة أخطاء 404"""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'المسار غير موجود'}), 404
        return send_from_directory(app.static_folder, 'index.html')

    @app.errorhandler(500)
    def internal_error(error):
        """معالجة أخطاء 500"""
        return jsonify({'error': 'خطأ داخلي في الخادم'}), 500

    return app