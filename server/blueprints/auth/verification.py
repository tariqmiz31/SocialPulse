"""Multi-step verification system for role changes"""
import os
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from psycopg2.pool import SimpleConnectionPool
from server.database import get_db
from flask import current_app, g

logger = logging.getLogger('silvarium_auth')

class VerificationManager:
    """إدارة عملية التحقق متعددة المراحل"""

    def __init__(self):
        """Initialize without database connection"""
        pass

    def _get_db(self):
        """Get database connection safely within application context"""
        if not hasattr(g, 'db'):
            g.db = get_db()
        return g.db

    def generate_verification_code(self, user_id: int, type: str = 'role_change',
                                 total_steps: int = 2) -> Tuple[str, datetime]:
        """
        توليد رمز تحقق جديد
        Returns: (verification_code, expiry_time)
        """
        try:
            db = self._get_db()
            if not db:
                logger.error("تعذر الاتصال بقاعدة البيانات")
                raise RuntimeError("Database connection failed")

            code = secrets.token_hex(3)  # 6 أرقام
            expires_at = datetime.now() + timedelta(minutes=30)

            cur = db.cursor()
            try:
                cur.execute("""
                    INSERT INTO verification_codes 
                    (user_id, code, type, expires_at, total_steps)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, code, type, expires_at, total_steps))

                db.commit()
                logger.info(f"تم إنشاء رمز تحقق جديد للمستخدم {user_id}")
                return code, expires_at

            finally:
                cur.close()

        except Exception as e:
            logger.error(f"خطأ في إنشاء رمز التحقق: {str(e)}")
            if 'db' in locals():
                db.rollback()
            raise

    def verify_code(self, user_id: int, code: str, type: str = 'role_change') -> Dict:
        """
        التحقق من صحة الرمز وتحديث مرحلة التحقق
        """
        try:
            db = self._get_db()
            if not db:
                logger.error("تعذر الاتصال بقاعدة البيانات")
                return {
                    'valid': False,
                    'message': {
                        'ar': 'خطأ في الاتصال بقاعدة البيانات',
                        'en': 'Database connection error'
                    },
                    'step': 0,
                    'total_steps': 0,
                    'completed': False
                }

            cur = db.cursor()
            try:
                # التحقق من وجود رمز صالح
                cur.execute("""
                    SELECT id, verification_step, total_steps, expires_at, verified
                    FROM verification_codes
                    WHERE user_id = %s AND code = %s AND type = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (user_id, code, type))

                result = cur.fetchone()
                if not result:
                    return {
                        'valid': False,
                        'message': {
                            'ar': 'رمز التحقق غير صالح',
                            'en': 'Invalid verification code'
                        },
                        'step': 0,
                        'total_steps': 0,
                        'completed': False
                    }

                code_id, current_step, total_steps, expires_at, verified = result

                # التحقق من صلاحية الرمز
                if expires_at < datetime.now():
                    return {
                        'valid': False,
                        'message': {
                            'ar': 'انتهت صلاحية رمز التحقق',
                            'en': 'Verification code has expired'
                        },
                        'step': current_step,
                        'total_steps': total_steps,
                        'completed': False
                    }

                if verified:
                    return {
                        'valid': False,
                        'message': {
                            'ar': 'تم استخدام هذا الرمز مسبقاً',
                            'en': 'This code has already been used'
                        },
                        'step': current_step,
                        'total_steps': total_steps,
                        'completed': True
                    }

                # تحديث مرحلة التحقق
                next_step = current_step + 1
                is_complete = next_step >= total_steps

                cur.execute("""
                    UPDATE verification_codes
                    SET verification_step = %s,
                        verified = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (next_step, is_complete, code_id))

                db.commit()

                return {
                    'valid': True,
                    'message': {
                        'ar': 'تم التحقق بنجاح',
                        'en': 'Verification successful'
                    } if is_complete else {
                        'ar': 'تم التحقق من المرحلة الحالية',
                        'en': 'Current step verified'
                    },
                    'step': next_step,
                    'total_steps': total_steps,
                    'completed': is_complete
                }

            finally:
                cur.close()

        except Exception as e:
            logger.error(f"خطأ في التحقق من الرمز: {str(e)}")
            if 'db' in locals():
                db.rollback()
            return {
                'valid': False,
                'message': {
                    'ar': 'حدث خطأ في عملية التحقق',
                    'en': 'Error during verification process'
                },
                'step': 0,
                'total_steps': 0,
                'completed': False
            }

    def get_verification_status(self, user_id: int, type: str = 'role_change') -> Dict:
        """
        الحصول على حالة التحقق الحالية للمستخدم
        """
        try:
            db = self._get_db()
            if not db:
                logger.error("تعذر الاتصال بقاعدة البيانات")
                return {
                    'status': 'error',
                    'message': 'Database connection failed',
                    'step': 0,
                    'total_steps': 0,
                    'completed': False
                }

            cur = db.cursor()
            try:
                cur.execute("""
                    SELECT verification_step, total_steps, verified
                    FROM verification_codes
                    WHERE user_id = %s AND type = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (user_id, type))

                result = cur.fetchone()
                if not result:
                    return {
                        'status': 'not_started',
                        'step': 0,
                        'total_steps': 0,
                        'completed': False
                    }

                current_step, total_steps, verified = result

                return {
                    'status': 'completed' if verified else 'in_progress',
                    'step': current_step,
                    'total_steps': total_steps,
                    'completed': verified
                }

            finally:
                cur.close()

        except Exception as e:
            logger.error(f"خطأ في الحصول على حالة التحقق: {str(e)}")
            return {
                'status': 'error',
                'step': 0,
                'total_steps': 0,
                'completed': False
            }

# Create verification manager instance
verification_manager = VerificationManager()