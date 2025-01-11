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
                logger.info("تم الحصول على اتصال جديد من المجمع")
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
            logger.info("تم إرجاع الاتصال إلى المجمع")
        except Exception as e:
            logger.error(f"خطأ في إرجاع الاتصال إلى المجمع: {str(e)}")
            try:
                db.close()
            except:
                pass

def init_db(app):
    """Initialize database connection pool"""
    global pool
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

        pool = SimpleConnectionPool(
            minconn=1,
            maxconn=20,
            dsn=database_url
        )

        # Test the connection
        conn = pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT version()')
                version = cur.fetchone()[0]
                logger.info(f"تم الاتصال بقاعدة البيانات بنجاح: {version}")
            pool.putconn(conn)
        except Exception as e:
            if conn:
                try:
                    pool.putconn(conn)
                except:
                    pass
            raise e

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
        raise