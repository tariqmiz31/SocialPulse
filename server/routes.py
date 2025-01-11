from flask import Flask, send_from_directory, jsonify, request
import os
from flask_mail import Message, Mail
from functools import wraps
import secrets
import datetime
import logging
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics

# Initialize Flask-Mail, metrics and logger
mail = Mail()
metrics = None
logger = logging.getLogger('silvarium')

def register_routes(app: Flask) -> Flask:
    """تسجيل مسارات التطبيق"""
    global metrics

    # تهيئة خدمة البريد الإلكتروني
    mail.init_app(app)

    # تهيئة نظام المراقبة
    metrics = PrometheusMetrics(app)
    metrics.info('app_info', 'Application info', version='1.0.0')

    # تكوين CORS للمسارات
    CORS(app, 
         supports_credentials=True,
         resources={
             r"/api/*": {
                 "origins": ["http://localhost:8080", "https://*.repl.co", "http://0.0.0.0:8080"],
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

    # نقطة نهاية للتحقق من صحة التطبيق
    @app.route('/api/health')
    @metrics.do_not_track()
    def health_check():
        """التحقق من صحة التطبيق"""
        try:
            # تحقق من اتصال قاعدة البيانات
            from server.database import get_db
            db = get_db()
            if not db:
                return jsonify({
                    'status': 'error',
                    'message': 'فشل الاتصال بقاعدة البيانات',
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }), 500

            return jsonify({
                'status': 'healthy',
                'message': 'التطبيق يعمل بشكل صحيح',
                'version': '1.0.0',
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"خطأ في فحص صحة التطبيق: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'حدث خطأ في فحص صحة التطبيق',
                'timestamp': datetime.datetime.utcnow().isoformat()
            }), 500

    # نقطة نهاية لمراقبة المقاييس
    @app.route('/api/metrics')
    @metrics.do_not_track()
    def metrics_endpoint():
        """الحصول على مقاييس التطبيق"""
        from prometheus_client import generate_latest
        return generate_latest()

    # المسار الرئيسي وخدمة الملفات الثابتة
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        """خدمة الملفات الثابتة للتطبيق"""
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    return app