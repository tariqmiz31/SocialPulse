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

                # Test the connection
                conn = pool.getconn()
                try:
                    with conn.cursor() as cur:
                        cur.execute('SELECT version()')
                        version = cur.fetchone()[0]
                        logger.info(f"تم الاتصال بقاعدة البيانات بنجاح: {version}")

                        # التحقق من وجود الجداول المطلوبة
                        cur.execute("""
                            SELECT table_name 
                            FROM information_schema.tables 
                            WHERE table_schema = 'public'
                        """)
                        existing_tables = {row[0] for row in cur.fetchall()}
                        required_tables = {
                            'verification_codes', 
                            'role_change_history', 
                            'verification_attempts'
                        }

                        missing_tables = required_tables - existing_tables
                        if missing_tables:
                            logger.warning(f"الجداول المفقودة: {', '.join(missing_tables)}")
                            # لا نقوم بإنشاء الجداول تلقائياً لتجنب تغيير هيكل قاعدة البيانات
                        else:
                            logger.info("جميع الجداول المطلوبة موجودة")

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
