"""Firebase Authentication service"""
import firebase_admin
from firebase_admin import auth, credentials
import os
import json
import logging
from typing import Optional, Dict, Any, Tuple
import time
import asyncio
from datetime import datetime, timedelta
import random
import string
import psycopg2

logger = logging.getLogger('silvarium_auth')

class FirebaseAuthService:
    def __init__(self):
        """Initialize Firebase Auth Service"""
        try:
            # Load service account JSON file
            service_account_path = 'attached_assets/silva-deb1c-firebase-adminsdk-g19p8-5d6dc42cd6.json'

            if not os.path.exists(service_account_path):
                logger.error("Service account file not found | ملف حساب الخدمة غير موجود")
                return

            with open(service_account_path, 'r') as file:
                cred_dict = json.load(file)

            # Set environment variables
            os.environ['FIREBASE_PROJECT_ID'] = cred_dict['project_id']
            os.environ['FIREBASE_PRIVATE_KEY'] = cred_dict['private_key']
            os.environ['FIREBASE_CLIENT_EMAIL'] = cred_dict['client_email']

            # Initialize Firebase Admin SDK if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                logger.info("تم تهيئة خدمة Firebase بنجاح | Firebase service initialized successfully")
            else:
                logger.info("Firebase already initialized | تم تهيئة Firebase مسبقاً")

        except Exception as e:
            logger.error(f"خطأ في تهيئة Firebase: {str(e)} | Firebase initialization error: {str(e)}")

    async def send_verification_code(self, phone_number: str) -> Dict[str, Any]:
        """Send SMS verification code | إرسال رمز التحقق عبر SMS"""
        try:
            # Rate limiting check
            if not await self._check_rate_limit(phone_number):
                logger.warning(f"تم تجاوز الحد المسموح لإرسال الرموز: {phone_number}")
                return {
                    'success': False,
                    'message': {
                        'ar': 'تم تجاوز الحد المسموح من المحاولات، يرجى المحاولة لاحقاً',
                        'en': 'Rate limit exceeded, please try again later'
                    }
                }

            # Generate code | توليد الرمز
            verification_code = ''.join(random.choices(string.digits, k=4))
            logger.info(f"تم توليد رمز التحقق: {verification_code}")

            # Save code in database | حفظ الرمز في قاعدة البيانات
            await self._save_verification_code(phone_number, verification_code)

            # Here you would integrate with your SMS service to actually send the code
            # For development, we'll log the code
            logger.info(f"رمز التحقق للرقم {phone_number}: {verification_code}")

            return {
                'success': True,
                'message': {
                    'ar': 'تم إرسال رمز التحقق بنجاح',
                    'en': 'Verification code sent successfully'
                }
            }

        except Exception as e:
            logger.error(f"خطأ في إرسال رمز التحقق: {str(e)}")
            return {
                'success': False,
                'message': {
                    'ar': 'فشل في إرسال رمز التحقق',
                    'en': 'Failed to send verification code'
                }
            }

    async def _check_rate_limit(self, phone_number: str) -> bool:
        """Check rate limit for SMS sending | التحقق من حد الإرسال"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            # Get number of attempts in the last hour
            cur.execute("""
                SELECT COUNT(*) 
                FROM verification_attempts 
                WHERE phone_number = %s 
                AND attempt_time > NOW() - INTERVAL '1 hour'
            """, (phone_number,))

            count = cur.fetchone()[0]

            # Insert new attempt
            cur.execute("""
                INSERT INTO verification_attempts (phone_number, attempt_time)
                VALUES (%s, NOW())
            """, (phone_number,))

            conn.commit()
            cur.close()
            conn.close()

            # Allow maximum 5 attempts per hour
            return count < 5

        except Exception as e:
            logger.error(f"خطأ في التحقق من حد الإرسال: {str(e)}")
            # In case of error, allow the attempt
            return True

    async def _save_verification_code(self, phone_number: str, code: str) -> None:
        """Save verification code in database | حفظ رمز التحقق في قاعدة البيانات"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            # Update or insert verification code
            expires_at = datetime.now() + timedelta(minutes=10)
            cur.execute("""
                UPDATE users 
                SET verification_code = %s,
                    verification_code_expires_at = %s
                WHERE phone_number = %s
            """, (code, expires_at, phone_number))

            if cur.rowcount == 0:
                # If no user exists, create a temporary user
                temp_username = f"temp_{phone_number}_{int(time.time())}"
                cur.execute("""
                    INSERT INTO users (username, phone_number, verification_code, verification_code_expires_at, status)
                    VALUES (%s, %s, %s, %s, 'pending')
                """, (temp_username, phone_number, code, expires_at))

            conn.commit()
            cur.close()
            conn.close()
            logger.info(f"تم حفظ رمز التحقق بنجاح للرقم: {phone_number}")

        except Exception as e:
            logger.error(f"خطأ في حفظ رمز التحقق: {str(e)}")
            if 'conn' in locals():
                conn.close()
            raise

    async def verify_code(self, phone_number: str, code: str) -> Tuple[bool, Optional[str]]:
        """Verify SMS code | التحقق من رمز SMS"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                SELECT verification_code, verification_code_expires_at
                FROM users
                WHERE phone_number = %s
            """, (phone_number,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if not result:
                return False, "رقم الهاتف غير مسجل | Phone number not registered"

            stored_code, expires_at = result

            if datetime.now() > expires_at:
                return False, "انتهت صلاحية الرمز | Code expired"

            if code != stored_code:
                return False, "رمز التحقق غير صحيح | Invalid verification code"

            return True, None

        except Exception as e:
            logger.error(f"خطأ في التحقق من الرمز: {str(e)}")
            return False, f"خطأ في التحقق من الرمز | Error verifying code: {str(e)}"

# Initialize Firebase Auth Service
try:
    firebase_auth = FirebaseAuthService()
    logger.info("Firebase Auth Service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Auth Service: {str(e)}")
    firebase_auth = None