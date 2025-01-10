import os
from dotenv import load_dotenv
from waitress import serve
import psycopg2
from werkzeug.security import generate_password_hash
from flask import Flask, jsonify
from flask_cors import CORS
from routes import registerRoutes
import logging

# تكوين التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

def create_admin_user():
    """إنشاء مستخدم مشرف إذا لم يكن موجوداً"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # التحقق من وجود المشرف
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if cur.fetchone() is None:
            # إنشاء مستخدم مشرف جديد
            hashed_password = generate_password_hash('admin123')
            cur.execute(
                """
                INSERT INTO users (username, password, role, is_approved, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ('admin', hashed_password, 'admin', True, 'active')
            )
            conn.commit()
            logger.info("تم إنشاء حساب المشرف بنجاح")

        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في إنشاء حساب المشرف: {e}")

def create_app():
    """إنشاء وتكوين تطبيق Flask"""
    app = Flask(__name__, static_folder='../client/dist', static_url_path='/')

    # تكوين CORS
    CORS(app, 
         supports_credentials=True,
         resources={
             r"/api/*": {
                 "origins": ["http://localhost:5000", "https://*.repl.co", "https://*.repl.dev"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"]
             }
         })

    # تسجيل المسارات
    registerRoutes(app)

    @app.route('/api/status')
    def status():
        return jsonify({
            "status": "running",
            "timestamp": str(os.getenv('START_TIME', '')),
            "environment": os.getenv('FLASK_ENV', 'production'),
            "auth_method": "admin_approval_required"
        })

    return app

def main():
    """الدالة الرئيسية لبدء الخادم"""
    try:
        # تحميل متغيرات البيئة
        load_dotenv()

        # التحقق من متغيرات البيئة المطلوبة
        if not os.getenv('DATABASE_URL'):
            raise ValueError("DATABASE_URL غير موجود")

        # إنشاء مستخدم مشرف
        create_admin_user()

        # إنشاء التطبيق
        app = create_app()

        # تحديد المنفذ
        port = int(os.getenv("PORT", "5000"))

        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")

        # بدء الخادم
        serve(app, host="0.0.0.0", port=port, url_scheme='https')

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {e}")
        raise

if __name__ == "__main__":
    main()