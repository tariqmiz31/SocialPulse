from werkzeug.security import generate_password_hash
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def create_admin_user():
    # تشفير كلمة المرور
    hashed_password = generate_password_hash('admin123')
    
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
        """, ('Tariq', hashed_password))
        
        user_id = cur.fetchone()[0]
        conn.commit()
        print(f"تم إنشاء حساب المشرف Tariq بنجاح (ID: {user_id})")
        
    except Exception as e:
        print(f"خطأ في إنشاء حساب المشرف: {str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    create_admin_user()
