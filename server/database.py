import psycopg2
from psycopg2.pool import SimpleConnectionPool
import logging
import os
from flask import g, current_app

logger = logging.getLogger('silvarium')
pool = None

def get_db():
    """Get database connection from pool"""
    if 'db' not in g:
        try:
            g.db = pool.getconn() if pool else None
            if g.db:
                logger.debug("تم الحصول على اتصال جديد من المجمع")
                return g.db
            else:
                logger.error("لم يتم تهيئة مجمع الاتصالات")
                return None
        except Exception as e:
            logger.error(f"خطأ في الحصول على اتصال من المجمع: {str(e)}")
            return None
    return g.db

def close_db(e=None):
    """Close database connection and return to pool"""
    db = g.pop('db', None)
    if db is not None and pool:
        try:
            pool.putconn(db)
            logger.debug("تم إرجاع الاتصال إلى المجمع")
        except Exception as e:
            logger.error(f"خطأ في إرجاع الاتصال إلى المجمع: {str(e)}")
            try:
                db.close()
            except:
                pass

def init_required_tables(conn):
    """Initialize required tables if they don't exist"""
    try:
        with conn.cursor() as cur:
            # Users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'user',
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Verification codes table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS verification_codes (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    code VARCHAR(6) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    verified BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Role change history table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS role_change_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    admin_id INTEGER REFERENCES users(id),
                    old_role VARCHAR(50) NOT NULL,
                    new_role VARCHAR(50) NOT NULL,
                    verification_id INTEGER REFERENCES verification_codes(id),
                    change_reason TEXT,
                    client_ip VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Verification attempts table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS verification_attempts (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            logger.info("تم إنشاء/التحقق من وجود جميع الجداول المطلوبة")

    except Exception as e:
        conn.rollback()
        logger.error(f"خطأ في تهيئة الجداول: {str(e)}")
        raise

def init_db(app):
    """Initialize database connection pool with proper error handling and connection testing"""
    global pool
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

        # Create connection pool with retry mechanism
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=20,
                    dsn=database_url,
                    connect_timeout=10
                )

                # Test the connection and initialize tables
                conn = pool.getconn()
                try:
                    with conn.cursor() as cur:
                        cur.execute('SELECT version()')
                        version = cur.fetchone()[0]
                        logger.info(f"تم الاتصال بقاعدة البيانات بنجاح: {version}")

                    # Initialize required tables
                    init_required_tables(conn)

                    pool.putconn(conn)
                    break

                except Exception as e:
                    if conn:
                        try:
                            pool.putconn(conn)
                        except:
                            pass
                    raise e

            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    raise Exception(f"فشل الاتصال بقاعدة البيانات بعد {max_retries} محاولات: {str(e)}")
                logger.warning(f"فشلت محاولة الاتصال {retry_count} من {max_retries}: {str(e)}")
                import time
                time.sleep(2 ** retry_count)  # exponential backoff

        # Register connection cleanup
        app.teardown_appcontext(close_db)
        return pool

    except Exception as e:
        logger.error(f"خطأ في تهيئة قاعدة البيانات: {str(e)}")
        if pool:
            try:
                pool.closeall()
            except:
                pass
        return None