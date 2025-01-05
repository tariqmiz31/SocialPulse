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
            # Load credentials directly from service account file
            service_account_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                'attached_assets',
                'silva-deb1c-firebase-adminsdk-g19p8-2ab855fd52.json'
            )

            logger.info(f"Loading Firebase credentials from: {service_account_path}")

            if not os.path.exists(service_account_path):
                raise FileNotFoundError(f"Service account file not found at: {service_account_path}")

            with open(service_account_path, 'r') as f:
                service_account_info = json.load(f)
                logger.info("Successfully loaded service account info")

            # Initialize Firebase Admin SDK with credentials
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_info)
                firebase_admin.initialize_app(cred)
                logger.info("تم تهيئة خدمة Firebase بنجاح | Firebase service initialized successfully")

        except Exception as e:
            logger.error(f"خطأ في تهيئة Firebase: {str(e)} | Firebase initialization error: {str(e)}")
            raise

    def verify_phone_number(self, phone_number: str, verification_id: str, code: str) -> Tuple[bool, Optional[str]]:
        """التحقق من رقم الهاتف والرمز | Verify phone number and code"""
        try:
            # First, verify the ID token from the client
            try:
                decoded_token = auth.verify_id_token(verification_id)
                if not decoded_token:
                    logger.warning(f"رمز التحقق غير صالح لرقم الهاتف: {phone_number}")
                    return False, "رمز التحقق غير صالح | Invalid verification code"
            except auth.InvalidIdTokenError:
                logger.warning(f"جلسة التحقق منتهية الصلاحية لرقم الهاتف: {phone_number}")
                return False, "جلسة التحقق منتهية الصلاحية | Verification session expired"

            # Check if the phone number matches
            if decoded_token.get('phone_number') != phone_number:
                logger.warning(f"رقم الهاتف لا يتطابق مع جلسة التحقق: {phone_number}")
                return False, "رقم الهاتف غير متطابق | Phone number mismatch"

            # If verification is successful, return true
            logger.info(f"تم التحقق من رقم الهاتف بنجاح: {phone_number}")
            return True, None

        except Exception as e:
            logger.error(f"خطأ في التحقق من رقم الهاتف: {str(e)} | Phone verification error: {str(e)}")
            return False, f"خطأ في التحقق من رقم الهاتف | Phone verification error: {str(e)}"

    def create_custom_token(self, phone_number: str) -> Optional[str]:
        """إنشاء رمز مخصص للمستخدم | Create custom token for user"""
        try:
            custom_token = auth.create_custom_token(phone_number)
            return custom_token.decode('utf-8')
        except Exception as e:
            logger.error(f"خطأ في إنشاء الرمز المخصص: {str(e)} | Error creating custom token: {str(e)}")
            return None

    def verify_custom_token(self, custom_token: str) -> Optional[Dict[str, Any]]:
        """التحقق من صحة الرمز المخصص | Verify custom token"""
        try:
            decoded_token = auth.verify_id_token(custom_token)
            return decoded_token
        except Exception as e:
            logger.error(f"خطأ في التحقق من الرمز المخصص: {str(e)} | Error verifying custom token: {str(e)}")
            return None

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

firebase_auth = FirebaseAuthService()