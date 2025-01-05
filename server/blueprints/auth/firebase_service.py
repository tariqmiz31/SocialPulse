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
            # Load the service account JSON file
            service_account_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                'attached_assets',
                'silva-deb1c-firebase-adminsdk-g19p8-2ab855fd52.json'
            )

            if not os.path.exists(service_account_path):
                raise FileNotFoundError("ملف حساب خدمة Firebase غير موجود | Firebase service account file not found")

            with open(service_account_path, 'r') as f:
                service_account = json.load(f)

            cred = credentials.Certificate(service_account)

            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
                logger.info("تم تهيئة خدمة Firebase بنجاح | Firebase service initialized successfully")

        except Exception as e:
            logger.error(f"خطأ في تهيئة Firebase: {str(e)} | Firebase initialization error: {str(e)}")
            raise

    def verify_phone_number(self, phone_number: str, verification_id: str, code: str = None) -> Tuple[bool, Optional[str]]:
        """التحقق من صحة رقم الهاتف والرمز | Verify phone number and code"""
        try:
            # Check if phone number is registered
            try:
                user = auth.get_user_by_phone_number(phone_number)
                logger.info(f"تم العثور على المستخدم برقم الهاتف: {phone_number}")

                if code and verification_id:
                    # Verify the code if provided
                    try:
                        decoded_token = auth.verify_session_cookie(verification_id)
                        if decoded_token and decoded_token.get('phone_number') == phone_number:
                            logger.info(f"تم التحقق من الرمز بنجاح لرقم الهاتف: {phone_number}")
                            return True, None
                        else:
                            logger.warning(f"فشل التحقق من الرمز لرقم الهاتف: {phone_number}")
                            return False, "رمز التحقق غير صحيح"
                    except auth.InvalidSessionCookieError:
                        logger.warning(f"رمز التحقق غير صالح لرقم الهاتف: {phone_number}")
                        return False, "رمز التحقق غير صالح"

                return True, None

            except auth.UserNotFoundError:
                logger.warning(f"لم يتم العثور على مستخدم برقم الهاتف: {phone_number}")
                return False, "رقم الهاتف غير مسجل"
            except Exception as e:
                logger.error(f"خطأ في البحث عن المستخدم برقم الهاتف: {str(e)}")
                return False, str(e)

        except Exception as e:
            logger.error(f"خطأ في التحقق من رقم الهاتف: {str(e)} | Phone verification error: {str(e)}")
            return False, str(e)

    def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """الحصول على معلومات المستخدم برقم الهاتف | Get user by phone number"""
        try:
            user = auth.get_user_by_phone_number(phone_number)
            return {
                'uid': user.uid,
                'phone_number': user.phone_number,
                'provider_data': user.provider_data
            }
        except auth.UserNotFoundError:
            logger.warning(f"لم يتم العثور على مستخدم برقم الهاتف: {phone_number}")
            return None
        except Exception as e:
            logger.error(f"خطأ في جلب بيانات المستخدم: {str(e)} | Error fetching user data: {str(e)}")
            return None

    def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """التحقق من رمز Firebase وإرجاع معلومات المستخدم | Verify Firebase ID token and return user info"""
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"خطأ في التحقق من الرمز: {str(e)} | Token verification error: {str(e)}")
            return None

firebase_auth = FirebaseAuthService()