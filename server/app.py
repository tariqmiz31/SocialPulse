from flask import Flask, jsonify, request, session
from flask_cors import CORS
from waitress import serve
import os
import logging
from werkzeug.security import generate_password_hash
import psycopg2
import time
import socket

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('silvarium')

# إنشاء تطبيق Flask
app = Flask(__name__)
CORS(app)

def is_port_in_use(port: int) -> bool:
    """التحقق مما إذا كان المنفذ قيد الاستخدام"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

def wait_for_port(port: int, timeout: int = 60) -> bool:
    """انتظار حتى يصبح المنفذ متاحًا"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            return True
        time.sleep(1)
    return False

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
        raise

@app.route('/')
def index():
    return jsonify({
        'status': 'running',
        'version': '1.0.0'
    })

@app.route('/api/admin/check')
def admin_check():
    """التحقق من صلاحيات المشرف"""
    if session.get('user_role') == 'admin':
        return jsonify({'isAdmin': True})
    return jsonify({'isAdmin': False}), 403

def main():
    try:
        # التحقق من متغيرات البيئة
        if not os.getenv('DATABASE_URL'):
            raise ValueError("DATABASE_URL غير موجود")

        # تكوين التطبيق
        app.config.update(
            SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            PERMANENT_SESSION_LIFETIME=1800
        )

        # إنشاء مستخدم مشرف
        create_admin_user()

        # تحديد المنفذ
        port = int(os.getenv('PORT', '5001'))

        # انتظار حتى يصبح المنفذ متاحًا
        if not wait_for_port(port):
            logger.warning(f"المنفذ {port} مشغول، جاري المحاولة على المنفذ التالي")
            port += 1

            if not wait_for_port(port):
                raise RuntimeError("لا توجد منافذ متاحة")

        logger.info(f"بدء تشغيل الخادم على المنفذ {port}")

        serve(
            app,
            host='0.0.0.0',
            port=port,
            url_scheme='https',
            threads=4,
            connection_limit=1000,
            channel_timeout=30
        )

        return True
    except Exception as e:
        logger.error(f"خطأ في بدء التشغيل: {e}")
        raise

if __name__ == '__main__':
    main()