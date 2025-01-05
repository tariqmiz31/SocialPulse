"""Firebase Authentication Service"""
import firebase_admin
from firebase_admin import auth, credentials
import os
import json
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger('silvarium_auth')

class FirebaseAuthService:
    def __init__(self):
        """Initialize Firebase Auth Service"""
        try:
            # Load Firebase credentials
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": os.getenv('FIREBASE_PROJECT_ID'),
                "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
                "client_email": os.getenv('FIREBASE_CLIENT_EMAIL')
            })

            # Initialize Firebase Admin SDK
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
                logger.info("تم تهيئة خدمة Firebase بنجاح | Firebase service initialized successfully")

        except Exception as e:
            logger.error(f"خطأ في تهيئة Firebase: {str(e)} | Firebase initialization error: {str(e)}")
            raise

    async def send_verification_code(self, phone_number: str) -> dict:
        """إرسال رمز التحقق عبر SMS | Send verification code via SMS"""
        try:
            # التحقق من تنسيق رقم الهاتف | Validate phone number format
            if not phone_number.startswith('+'):
                logger.warning(f"رقم هاتف بتنسيق غير صحيح: {phone_number}")
                return {
                    'success': False,
                    'message': {
                        'ar': 'يجب أن يبدأ رقم الهاتف بـ + متبوعاً برمز الدولة',
                        'en': 'Phone number must start with + followed by country code'
                    }
                }

            # إعداد خيارات التحقق | Setup verification options
            verification_settings = {
                'phoneNumber': phone_number,
                'recaptchaToken': True,
                'sms': {
                    'androidPackageName': 'com.silvarium.social',
                    'template': 'رمز التحقق الخاص بك هو: %CODE% | Your verification code is: %CODE%'
                }
            }

            # إرسال رمز التحقق | Send verification code
            verification = auth.create_phone_verification(verification_settings)
            logger.info(f"تم إرسال رمز التحقق بنجاح للرقم: {phone_number}")

            return {
                'success': True,
                'message': {
                    'ar': 'تم إرسال رمز التحقق بنجاح',
                    'en': 'Verification code sent successfully'
                },
                'session_info': verification.session_info
            }

        except auth.QuotaExceededError:
            logger.error(f"تم تجاوز الحد الأقصى لإرسال الرسائل للرقم: {phone_number}")
            return {
                'success': False,
                'message': {
                    'ar': 'تم تجاوز الحد الأقصى لإرسال الرسائل، يرجى المحاولة لاحقاً',
                    'en': 'SMS quota exceeded, please try again later'
                }
            }
        except auth.InvalidPhoneNumberError:
            logger.error(f"رقم هاتف غير صالح: {phone_number}")
            return {
                'success': False,
                'message': {
                    'ar': 'رقم الهاتف غير صالح',
                    'en': 'Invalid phone number'
                }
            }
        except auth.PhoneNumberAlreadyExistsError:
            logger.error(f"رقم الهاتف مستخدم بالفعل: {phone_number}")
            return {
                'success': False,
                'message': {
                    'ar': 'رقم الهاتف مستخدم بالفعل',
                    'en': 'Phone number is already in use'
                }
            }
        except Exception as e:
            logger.error(f"خطأ في إرسال رمز التحقق: {str(e)}")
            return {
                'success': False,
                'message': {
                    'ar': f'فشل في إرسال رمز التحقق: {str(e)}',
                    'en': f'Failed to send verification code: {str(e)}'
                }
            }

    def verify_phone_number(self, phone_number: str, verification_id: str, code: str) -> Tuple[bool, Optional[str]]:
        """التحقق من رقم الهاتف والرمز | Verify phone number and code"""
        try:
            # التحقق من صحة البيانات | Validate input data
            if not all([phone_number, verification_id, code]):
                logger.warning("بيانات التحقق غير مكتملة")
                return False, "يجب توفير جميع بيانات التحقق | All verification data must be provided"

            # التحقق من رمز الجلسة | Verify session token
            try:
                decoded_token = auth.verify_id_token(verification_id)
                if not decoded_token:
                    logger.warning(f"رمز التحقق غير صالح لرقم الهاتف: {phone_number}")
                    return False, "رمز التحقق غير صالح | Invalid verification code"
            except auth.InvalidIdTokenError:
                logger.warning(f"جلسة التحقق منتهية الصلاحية لرقم الهاتف: {phone_number}")
                return False, "جلسة التحقق منتهية الصلاحية | Verification session expired"

            # التحقق من تطابق رقم الهاتف | Verify phone number match
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
        except auth.RevokedIdTokenError:
            logger.error("تم إلغاء رمز التحقق")
            return False, "تم إلغاء رمز التحقق | Verification code revoked"
        except Exception as e:
            logger.error(f"خطأ في التحقق من رقم الهاتف: {str(e)}")
            return False, f"خطأ في التحقق من رقم الهاتف | Phone verification error: {str(e)}"

firebase_auth = FirebaseAuthService()