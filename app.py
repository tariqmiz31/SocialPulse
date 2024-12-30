from flask import Flask, send_from_directory, request, jsonify, redirect, url_for
from flask_cors import CORS
import os
from app.services.social_media_service import SocialMediaService

app = Flask(__name__, static_folder='dist/public', static_url_path='/')

# Configure CORS for your Cloudflare domain
CORS(app, resources={
    r"/*": {
        "origins": os.getenv('ALLOWED_ORIGINS', '*').split(','),
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
    }
})

# Initialize services
social_media_service = SocialMediaService()

# Add security headers
@app.after_request
def add_security_headers(response):
    # Security headers for Cloudflare
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

# Social Media Platform Authentication Routes
@app.route('/api/auth/<platform>/connect')
async def connect_platform(platform):
    """Start OAuth flow for a platform"""
    try:
        oauth_url = social_media_service.get_oauth_url(platform)
        return jsonify({"auth_url": oauth_url})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to generate authentication URL"}), 500

@app.route('/api/auth/<platform>/callback')
async def platform_callback(platform):
    """Handle OAuth callback from platforms"""
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({"error": "Authorization code not provided"}), 400

        # Exchange code for access token
        token_data = await social_media_service.handle_oauth_callback(platform, code)

        # Here you would typically:
        # 1. Store the tokens in your database
        # 2. Associate them with the current user
        # 3. Redirect to the frontend with success message

        return redirect(f"{os.getenv('APP_URL', '')}/settings?connection=success&platform={platform}")
    except Exception as e:
        return redirect(f"{os.getenv('APP_URL', '')}/settings?connection=error&platform={platform}&error={str(e)}")

@app.route('/api/social/post', methods=['POST'])
async def publish_content():
    """Publish content to selected platforms"""
    try:
        data = request.json
        if not data or 'content' not in data or 'platforms' not in data:
            return jsonify({"error": "Missing required fields"}), 400

        content = data['content']
        platforms = data['platforms']
        media_urls = data.get('media_urls', [])

        results = {}
        for platform in platforms:
            try:
                # Get access token from database for this platform
                # This would normally come from your database based on the authenticated user
                access_token = "PLATFORM_ACCESS_TOKEN"  # Placeholder

                result = await social_media_service.publish_content(
                    platform=platform,
                    content=content,
                    media_urls=media_urls,
                    access_token=access_token
                )
                results[platform] = {"status": "success", "data": result}
            except Exception as e:
                results[platform] = {"status": "error", "error": str(e)}

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Static file serving
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Use waitress for production
    from waitress import serve
    serve(
        app,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        url_scheme='https'  # Force HTTPS for Cloudflare
    )