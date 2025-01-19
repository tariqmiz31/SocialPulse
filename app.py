from flask import Flask, send_from_directory, request, jsonify, redirect, url_for
from flask_cors import CORS
import os
import logging
from app.services.social_media_service import SocialMediaService

# إعداد تسجيل الأخطاء
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SocialPulse")

app = Flask(__name__, static_folder='dist/public', static_url_path='/')

# تسجيل الطلبات الواردة
@app.before_request
def log_request_info():
    logger.info(f"Request received: {request.method} {request.path}")

# نقطة نهاية للحصول على معلومات المستخدم
@app.route('/api/user', methods=['GET'])
def get_user_info():
    try:
        user_info = {
            "id": 1,
            "name": "Tariq",
            "email": "si;variumsa@gmail.com",
            "heapUsed": 0  # 
        }
        logger.info(f"User info sent: {user_info}")
        return jsonify(user_info), 200
    except Exception as e:
        logger.error(f"Error in /api/user: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch user information"}), 500

        # تسجيل البيانات قبل إعادتها
        logger.info(f"User info sent: {user_info}")
        return jsonify(user_info), 200
    except Exception as e:
        logger.error(f"Error in /api/user: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch user information"}), 500

# إعداد CORS
CORS(app, resources={
    r"/*": {
        "origins": os.getenv('ALLOWED_ORIGINS', '*').split(','),
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
    }
})

# نقاط نهاية للمراقبة
@app.route('/api/monitoring/health', methods=['GET'])
def monitoring_health():
    """للتحقق من صحة التطبيق"""
    health_data = {"status": "healthy"}
    logger.info(f"Health status: {health_data}")
    return jsonify(health_data), 200

@app.route('/api/monitoring/status', methods=['GET'])
def monitoring_status():
    """للتحقق من حالة التطبيق"""
    status_data = {"status": "running", "uptime": "24h"}
    logger.info(f"Status data: {status_data}")
    return jsonify(status_data), 200

@app.route('/api/monitoring/logs', methods=['GET'])
def monitoring_logs():
    """عرض السجلات"""
    logs_data = {"logs": []}
    logger.info(f"Logs data: {logs_data}")
    return jsonify(logs_data), 200

@app.route('/api/monitoring/errors', methods=['GET'])
def monitoring_errors():
    """عرض الأخطاء"""
    errors_data = {"errors": []}
    logger.info(f"Errors data: {errors_data}")
    return jsonify(errors_data), 200

# تهيئة الخدمات
social_media_service = SocialMediaService()

# إضافة ترويسات الأمان
@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

# نقاط نهاية مصادقة منصات التواصل الاجتماعي
@app.route('/api/auth/<platform>/connect')
async def connect_platform(platform):
    try:
        oauth_url = social_media_service.get_oauth_url(platform)
        logger.info(f"OAuth URL for {platform}: {oauth_url}")
        return jsonify({"auth_url": oauth_url})
    except ValueError as e:
        logger.error(f"Error in OAuth connection for {platform}: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in OAuth connection for {platform}: {e}", exc_info=True)
        return jsonify({"error": "Failed to generate authentication URL"}), 500

@app.route('/api/auth/<platform>/callback')
async def platform_callback(platform):
    try:
        code = request.args.get('code')
        if not code:
            logger.error("Authorization code not provided")
            return jsonify({"error": "Authorization code not provided"}), 400

        token_data = await social_media_service.handle_oauth_callback(platform, code)
        logger.info(f"Token data for {platform}: {token_data}")
        return jsonify(token_data)
    except ValueError as e:
        logger.error(f"Error in callback for {platform}: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in callback for {platform}: {e}", exc_info=True)
        return jsonify({"error": "Authentication failed"}), 500

# نقطة نهاية لنشر المحتوى
@app.route('/api/social/post', methods=['POST'])
async def publish_content():
    try:
        data = request.json
        if not data or 'content' not in data or 'platforms' not in data:
            logger.error("Missing required fields in request")
            return jsonify({"error": "Missing required fields"}), 400

        content = data['content']
        platforms = data['platforms']
        media_urls = data.get('media_urls', [])

        results = {}
        for platform in platforms:
            try:
                access_token = "PLATFORM_ACCESS_TOKEN"  # Placeholder
                result = await social_media_service.publish_content(
                    platform=platform,
                    content=content,
                    media_urls=media_urls,
                    access_token=access_token
                )
                logger.info(f"Published content to {platform}: {result}")
                results[platform] = {"status": "success", "data": result}
            except Exception as e:
                error_type = type(e).__name__
                error_details = {"type": error_type, "message": str(e)}
                results[platform] = {"status": "error", "error": error_details}
                logger.error(f"Error publishing to {platform}: {error_details}")

        return jsonify(results)
    except Exception as e:
        logger.error(f"Unexpected error in publish_content: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# تقديم الملفات الثابتة
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        logger.info(f"Serving static file: {path}")
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    logger.info("Starting the application...")
    try:
        from waitress import serve
        port = int(os.getenv('PORT', 5000))
        logger.info(f"Waitress server running on http://127.0.0.1:{port}")
        serve(app, host='0.0.0.0', port=port, url_scheme='https')
    except Exception as e:
        logger.error(f"Failed to start the server: {e}", exc_info=True)
if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=5000)
