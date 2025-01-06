"""Firebase Authentication service"""
import firebase_admin
from firebase_admin import auth, credentials
import os
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import psycopg2

logger = logging.getLogger('silvarium_auth')

class FirebaseAuthService:
    def __init__(self):
        """Initialize Firebase Auth Service"""
        try:
            # Load service account from environment variables
            cred_dict = {
                "type": "service_account",
                "project_id": os.getenv('FIREBASE_PROJECT_ID'),
                "private_key": os.getenv('FIREBASE_PRIVATE_KEY'),
                "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
                "token_uri": "https://oauth2.googleapis.com/token",
            }

            # Initialize Firebase Admin SDK if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                logger.info("تم تهيئة خدمة Firebase بنجاح | Firebase service initialized successfully")
            else:
                logger.info("Firebase already initialized | تم تهيئة Firebase مسبقاً")

        except Exception as e:
            logger.error(f"خطأ في تهيئة Firebase: {str(e)} | Firebase initialization error: {str(e)}")

    async def start_phone_verification(self, phone_number: str) -> Dict[str, Any]:
        """Start phone verification process | بدء عملية التحقق من رقم الهاتف"""
        try:
            # Validate Saudi phone number
            if not phone_number.startswith('+966') or len(phone_number) != 13:
                logger.warning(f"رقم هاتف غير صالح: {phone_number}")
                return {
                    'success': False,
                    'message': {
                        'ar': 'رقم الهاتف غير صالح، يجب أن يبدأ بـ +966',
                        'en': 'Invalid phone number, must start with +966'
                    }
                }

            # Create a session cookie for phone auth
            try:
                verification_id = auth.create_session_cookie(
                    phone_number,
                    expires_in=timedelta(minutes=10)
                )
                logger.info(f"تم إنشاء جلسة تحقق للرقم: {phone_number}")

                return {
                    'success': True,
                    'verificationId': verification_id,
                    'message': {
                        'ar': 'تم إرسال رمز التحقق بنجاح',
                        'en': 'Verification code sent successfully'
                    }
                }
            except auth.AuthError as e:
                logger.error(f"خطأ في إنشاء جلسة التحقق: {str(e)}")
                return {
                    'success': False,
                    'message': {
                        'ar': 'فشل في إرسال رمز التحقق',
                        'en': 'Failed to send verification code'
                    }
                }

        except Exception as e:
            logger.error(f"خطأ في بدء عملية التحقق: {str(e)}")
            return {
                'success': False,
                'message': {
                    'ar': 'حدث خطأ في عملية التحقق',
                    'en': 'Error in verification process'
                }
            }

    async def verify_phone_number(self, verification_id: str, code: str) -> Tuple[bool, Optional[str]]:
        """Verify phone number with code | التحقق من رقم الهاتف باستخدام الرمز"""
        try:
            # Validate code format
            if len(code) != 4 or not code.isdigit():
                return False, "رمز التحقق يجب أن يكون 4 أرقام"

            # Verify the code with Firebase
            try:
                decoded_claims = auth.verify_session_cookie(verification_id, check_revoked=True)
                phone_number = decoded_claims.get('phone_number')

                if not phone_number:
                    return False, "جلسة التحقق غير صالحة"

                # Update user status in database
                conn = psycopg2.connect(os.getenv('DATABASE_URL'))
                cur = conn.cursor()

                cur.execute("""
                    UPDATE users 
                    SET status = 'active',
                        phone_verified = true
                    WHERE phone_number = %s
                """, (phone_number,))

                conn.commit()
                cur.close()
                conn.close()

                return True, None

            except auth.InvalidSessionCookieError:
                return False, "انتهت صلاحية جلسة التحقق"
            except auth.RevokedSessionCookieError:
                return False, "تم إلغاء جلسة التحقق"

        except Exception as e:
            logger.error(f"خطأ في التحقق من الرمز: {str(e)}")
            return False, str(e)

# Initialize Firebase Auth Service
try:
    firebase_auth = FirebaseAuthService()
    logger.info("Firebase Auth Service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Auth Service: {str(e)}")
    firebase_auth = None