from flask import Flask, jsonify, request, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from flask_babel import Babel, gettext
from datetime import datetime
import os
import logging
from app.services.content_repurposer import ContentRepurposer
from app.services.caption_generator import CaptionGenerator
from app.services.performance_predictor import PerformancePredictor
from app.services.ab_test_suggester import ABTestSuggester

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize Babel
babel = Babel(app)

# Supported languages
LANGUAGES = {
    'en': 'English',
    'ar': 'العربية'
}

@babel.localeselector
def get_locale():
    # Try to get the language from the session
    if session.get('lang'):
        return session.get('lang')
    # Otherwise try to guess the language from the user accept header
    return request.accept_languages.best_match(LANGUAGES.keys())

# Database configuration
if not os.getenv('DATABASE_URL'):
    raise RuntimeError("DATABASE_URL environment variable is not set")

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['LANGUAGES'] = LANGUAGES

logger.info("Initializing database connection...")

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    platform_connections = db.relationship('PlatformConnection', backref='user', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    platforms = db.Column(db.JSON, nullable=False)
    scheduled_for = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    analytics = db.relationship('Analytics', backref='post', lazy=True)

class PlatformConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    access_token = db.Column(db.String(255), nullable=False)
    refresh_token = db.Column(db.String(255))
    expires_at = db.Column(db.DateTime)

class Analytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    likes = db.Column(db.Integer, default=0)
    shares = db.Column(db.Integer, default=0)
    comments = db.Column(db.Integer, default=0)
    reach = db.Column(db.Integer, default=0)
    engagement_rate = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Language routes
@app.route('/api/language', methods=['GET', 'POST'])
def language():
    if request.method == 'POST':
        lang = request.json.get('lang')
        if lang and lang in LANGUAGES:
            session['lang'] = lang
            return jsonify({'status': 'success', 'lang': lang})
        return jsonify({'status': 'error', 'message': 'Invalid language'}), 400

    return jsonify({
        'current': session.get('lang', get_locale()),
        'available': LANGUAGES
    })

# Routes with internationalization
@app.route('/')
def index():
    logger.info("Serving index page")
    return render_template('index.html')

@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        logger.info("Fetching all posts")
        posts = Post.query.all()
        return jsonify([{
            'id': post.id,
            'content': post.content,
            'platforms': post.platforms,
            'scheduled_for': post.scheduled_for.isoformat(),
            'status': post.status,
            'message': gettext('Post retrieved successfully')
        } for post in posts])
    except Exception as e:
        logger.error(f"Error fetching posts: {str(e)}")
        return jsonify({"error": gettext('Failed to fetch posts')}), 500

@app.route('/api/posts', methods=['POST'])
def create_post():
    try:
        data = request.get_json()
        logger.info(f"Creating new post with data: {data}")

        post = Post(
            content=data['content'],
            platforms=data['platforms'],
            scheduled_for=datetime.fromisoformat(data.get('scheduled_for', datetime.utcnow().isoformat())),
            status='scheduled',
            user_id=1  # TODO: Get from auth session
        )
        db.session.add(post)
        db.session.commit()

        logger.info(f"Successfully created post with ID: {post.id}")
        return jsonify({
            'id': post.id,
            'content': post.content,
            'platforms': post.platforms,
            'scheduled_for': post.scheduled_for.isoformat(),
            'status': post.status,
            'message': gettext('Post created successfully')
        })
    except Exception as e:
        logger.error(f"Error creating post: {str(e)}")
        return jsonify({"error": gettext('Failed to create post')}), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    try:
        logger.info("Fetching analytics")
        analytics = Analytics.query.all()
        return jsonify([{
            'post_id': analytic.post_id,
            'platform': analytic.platform,
            'likes': analytic.likes,
            'shares': analytic.shares,
            'comments': analytic.comments,
            'engagement_rate': analytic.engagement_rate,
            'message': gettext('Analytics retrieved successfully')
        } for analytic in analytics])
    except Exception as e:
        logger.error(f"Error fetching analytics: {str(e)}")
        return jsonify({"error": gettext('Failed to fetch analytics')}), 500

@app.route('/api/repurpose', methods=['POST'])
def repurpose_content():
    try:
        data = request.get_json()
        logger.info(f"Repurposing content for platforms: {data['platforms']}")

        content = data['content']
        platforms = data['platforms']

        repurposed = ContentRepurposer.repurpose_content(content, platforms)

        logger.info("Content repurposed successfully")
        return jsonify(repurposed)
    except Exception as e:
        logger.error(f"Error repurposing content: {str(e)}")
        return jsonify({"error": gettext('Failed to repurpose content')}), 500

@app.route('/api/generate-caption', methods=['POST'])
def generate_caption():
    try:
        data = request.get_json()
        logger.info(f"Generating caption for content type: {data.get('content_type')} on platform: {data.get('platform')}")

        generator = CaptionGenerator()
        result = generator.generate_caption(
            content_type=data.get('content_type', 'general'),
            target_platform=data.get('platform', 'instagram')
        )

        logger.info("Caption generated successfully")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error generating caption: {str(e)}")
        return jsonify({"error": gettext('Failed to generate caption')}), 500

@app.route('/api/predict-performance', methods=['POST'])
def predict_performance():
    try:
        data = request.get_json()
        logger.info(f"Predicting performance for content on platform: {data.get('platform')}")

        predictor = PerformancePredictor()
        result = predictor.predict_performance(
            content=data.get('content', ''),
            platform=data.get('platform', 'instagram'),
            content_type=data.get('content_type', 'general')
        )

        logger.info("Performance prediction completed successfully")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error predicting performance: {str(e)}")
        return jsonify({"error": gettext('Failed to predict performance')}), 500

@app.route('/api/ab-test-suggestions', methods=['POST'])
def get_ab_test_suggestions():
    try:
        data = request.get_json()
        logger.info(f"Generating A/B test suggestions for platform: {data.get('platform')}")

        suggester = ABTestSuggester()
        result = suggester.generate_test_suggestions(
            content=data.get('content', ''),
            platform=data.get('platform', 'instagram'),
            content_type=data.get('content_type', 'general')
        )

        logger.info("A/B test suggestions generated successfully")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error generating A/B test suggestions: {str(e)}")
        return jsonify({"error": gettext('Failed to generate A/B test suggestions')}), 500

if __name__ == '__main__':
    with app.app_context():
        logger.info("Creating database tables...")
        db.create_all()
    app.run(host='0.0.0.0', port=5000)