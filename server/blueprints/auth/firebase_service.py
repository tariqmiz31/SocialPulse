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
                'silva-11e9d-firebase-adminsdk-n8a88-74bc434752.json'
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

    def verify_phone_number(self, phone_number: str, verification_id: str) -> Tuple[bool, Optional[str]]:
        """التحقق من صحة رقم الهاتف وتسجيله | Verify if phone number is valid and registered"""
        try:
            user = self.get_user_by_phone(phone_number)
            if not user:
                return False, "رقم الهاتف غير مسجل | Phone number is not registered"

            # For demo purposes, we're considering the verification successful if the user exists
            # In a real implementation, you would verify the code with Firebase
            return True, None

        except Exception as e:
            logger.error(f"خطأ في التحقق من رقم الهاتف: {str(e)} | Phone verification error: {str(e)}")
            return False, f"خطأ في التحقق من رقم الهاتف: {str(e)} | Phone verification error: {str(e)}"

    def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """الحصول على معلومات المستخدم برقم الهاتف | Get user by phone number"""
        try:
            user = auth.get_user_by_phone_number(phone_number)
            return {
                'uid': user.uid,
                'phone_number': user.phone_number,
                'provider_data': user.provider_data
            }
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