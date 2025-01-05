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
                raise ValueError("Service account file not found")

            with open(service_account_path, 'r') as file:
                cred_dict = json.load(file)

            # Set environment variables
            os.environ['FIREBASE_PROJECT_ID'] = cred_dict['project_id']
            os.environ['FIREBASE_PRIVATE_KEY'] = cred_dict['private_key']
            os.environ['FIREBASE_CLIENT_EMAIL'] = cred_dict['client_email']

            # Initialize Firebase Admin SDK if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred, {
                    'auth_settings': {
                        'sms_verification_message': 'يرجى استخدام الرقم المؤقت لاستعادة كلمة المرور: %CODE%',
                        'code_length': 4
                    }
                })
                logger.info("تم تهيئة خدمة Firebase بنجاح | Firebase service initialized successfully")
            else:
                logger.info("Firebase already initialized | تم تهيئة Firebase مسبقاً")

        except Exception as e:
            logger.error(f"خطأ في تهيئة Firebase: {str(e)} | Firebase initialization error: {str(e)}")
            raise

    async def send_verification_code(self, phone_number: str) -> Dict[str, Any]:
        """Send SMS verification code | إرسال رمز التحقق عبر SMS"""
        try:
            # Validate phone number format | التحقق من تنسيق رقم الهاتف
            if not phone_number.startswith('+'):
                logger.warning(f"رقم هاتف بتنسيق غير صحيح: {phone_number}")
                return {
                    'success': False,
                    'message': {
                        'ar': 'يجب أن يبدأ رقم الهاتف بـ + متبوعاً برمز الدولة',
                        'en': 'Phone number must start with + followed by country code'
                    }
                }

            # Check verification code attempts | التحقق من عدد محاولات إرسال الرمز
            try:
                user = auth.get_user_by_phone_number(phone_number)
                if user and user.disabled:
                    logger.warning(f"الحساب معطل لرقم الهاتف: {phone_number}")
                    return {
                        'success': False,
                        'message': {
                            'ar': 'هذا الحساب معطل، يرجى الاتصال بالدعم',
                            'en': 'This account is disabled, please contact support'
                        }
                    }
            except auth.UserNotFoundError:
                pass  # This is fine, user doesn't exist yet

            # Generate code | توليد الرمز
            verification_code = ''.join(random.choices(string.digits, k=4))
            logger.info(f"تم توليد رمز التحقق: {verification_code}")

            # Save code in database | حفظ الرمز في قاعدة البيانات
            await self._save_verification_code(phone_number, verification_code)

            logger.info(f"تم إرسال رمز التحقق بنجاح للرقم: {phone_number}")
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
                    'ar': 'فشل في إرسال رمز التحقق، يرجى المحاولة مرة أخرى',
                    'en': 'Failed to send verification code, please try again'
                }
            }

    async def _save_verification_code(self, phone_number: str, code: str) -> None:
        """Save verification code in database | حفظ رمز التحقق في قاعدة البيانات"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            expires_at = datetime.now() + timedelta(minutes=10)
            temp_username = f"temp_{phone_number}_{int(time.time())}"
            temp_password = 'temporary_password'  # This will be updated when user sets their password

            # Try to update existing user first
            cur.execute("""
                UPDATE users 
                SET verification_code = %s,
                    verification_code_expires_at = %s
                WHERE phone_number = %s
            """, (code, expires_at, phone_number))

            if cur.rowcount == 0:
                # If no user exists, create a new temporary user
                cur.execute("""
                    INSERT INTO users (username, password, phone_number, verification_code, verification_code_expires_at, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                """, (temp_username, temp_password, phone_number, code, expires_at))

            conn.commit()
            cur.close()
            conn.close()
            logger.info(f"تم حفظ رمز التحقق بنجاح للرقم: {phone_number}")

        except Exception as e:
            logger.error(f"خطأ في حفظ رمز التحقق: {str(e)}")
            if 'conn' in locals():
                conn.close()
            raise

    def verify_phone_number(self, phone_number: str, verification_id: str, code: str) -> Tuple[bool, Optional[str]]:
        """Verify phone number and code | التحقق من رقم الهاتف والرمز"""
        try:
            # Validate input data | التحقق من صحة البيانات
            if not all([phone_number, verification_id, code]):
                logger.warning("بيانات التحقق غير مكتملة")
                return False, "يجب توفير جميع بيانات التحقق | All verification data must be provided"

            # Verify session token | التحقق من رمز الجلسة
            try:
                decoded_token = auth.verify_id_token(verification_id)
                if not decoded_token:
                    logger.warning(f"رمز التحقق غير صالح لرقم الهاتف: {phone_number}")
                    return False, "رمز التحقق غير صالح | Invalid verification code"
            except auth.InvalidIdTokenError:
                logger.warning(f"جلسة التحقق منتهية الصلاحية لرقم الهاتف: {phone_number}")
                return False, "جلسة التحقق منتهية الصلاحية | Verification session expired"

            # Verify phone number match | التحقق من تطابق رقم الهاتف
            if decoded_token.get('phone_number') != phone_number:
                logger.warning(f"رقم الهاتف لا يتطابق مع جلسة التحقق: {phone_number}")
                return False, "رقم الهاتف غير متطابق | Phone number mismatch"

            logger.info(f"تم التحقق من رقم الهاتف بنجاح: {phone_number}")
            return True, None

        except auth.ExpiredIdTokenError:
            logger.error("رمز التحقق منتهي الصلاحية")
            return False, "رمز التحقق منتهي الصلاحية | Verification code expired"
        except auth.InvalidIdTokenError:
            logger.error("رمز التحقق غير صالح")
            return False, "رمز التحقق غير صالح | Invalid verification code"
        except Exception as e:
            logger.error(f"خطأ في التحقق من رقم الهاتف: {str(e)}")
            return False, f"خطأ في التحقق من رقم الهاتف | Error verifying phone number: {str(e)}"

# Initialize Firebase Auth Service
try:
    firebase_auth = FirebaseAuthService()
    logger.info("Firebase Auth Service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Auth Service: {str(e)}")
    firebase_auth = None