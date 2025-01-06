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

        # Check if index.html exists in static folder
        index_path = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, 'index.html')
        else:
            # Return a simple message if index.html doesn't exist yet
            return jsonify({
                'message': {
                    'ar': 'التطبيق قيد التطوير',
                    'en': 'Application is under development'
                }
            })

    # معالجة الأخطاء
    @app.errorhandler(404)
    def not_found_error(error):
        """معالجة أخطاء 404"""
        if request.path.startswith('/api/'):
            return jsonify({
                'message': {
                    'ar': 'المسار غير موجود',
                    'en': 'Path not found'
                }
            }), 404

        index_path = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, 'index.html')
        else:
            return jsonify({
                'message': {
                    'ar': 'الصفحة غير موجودة',
                    'en': 'Page not found'
                }
            }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """معالجة أخطاء 500"""
        return jsonify({
            'message': {
                'ar': 'خطأ داخلي في الخادم',
                'en': 'Internal server error'
            }
        }), 500

    return app