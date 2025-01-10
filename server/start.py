import os
import psycopg2
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
import logging
from werkzeug.security import generate_password_hash
import socket

# تكوين التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

def find_available_port(start_port=5000, max_attempts=10):
    """البحث عن منفذ متاح"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except socket.error:
                continue
    raise RuntimeError("لم يتم العثور على منفذ متاح")

def create_admin_user():
    """إنشاء حساب المشرف Tariq"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # إنشاء المستخدم المشرف
        cur.execute("""
            INSERT INTO users (username, password, role, is_approved, status)
            VALUES (%s, %s, 'admin', true, 'active')
            ON CONFLICT (username) 
            DO UPDATE SET 
                password = EXCLUDED.password,
                role = 'admin',
                is_approved = true,
                status = 'active'
            RETURNING id;
        """, ('Tariq', generate_password_hash('admin123')))

        user_id = cur.fetchone()[0]
        conn.commit()

        print(f"تم إنشاء حساب المشرف Tariq بنجاح (ID: {user_id})")
        return user_id

    except Exception as e:
        print(f"خطأ في إنشاء حساب المشرف: {str(e)}")
        raise
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

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

    return app

def main():
    """الدالة الرئيسية لبدء الخادم"""
    try:
        # تحميل متغيرات البيئة
        load_dotenv()

        # التحقق من متغيرات البيئة المطلوبة
        if not os.getenv('DATABASE_URL'):
            raise ValueError("DATABASE_URL غير موجود")

        # إنشاء/تحديث مستخدم مشرف
        create_admin_user()

        # إنشاء التطبيق
        app = create_app()

        # البحث عن منفذ متاح
        port = find_available_port()

        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")

        # بدء الخادم
        app.run(host="0.0.0.0", port=port, debug=True)

    except Exception as e:
        logger.error(f"خطأ في بدء الخادم: {e}")
        raise

if __name__ == "__main__":
    main()