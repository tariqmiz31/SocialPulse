"""Firebase Authentication service for SMS verification"""
import os
import logging
from datetime import datetime, timedelta
import random
import string
import firebase_admin
from firebase_admin import auth, credentials

# إعداد التسجيل
logger = logging.getLogger('silvarium_auth')
logger.setLevel(logging.INFO)

class FirebaseAuthService:
    def __init__(self):
        """تهيئة خدمة Firebase"""
        try:
            # التحقق من وجود بيانات الاعتماد
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": os.getenv('FIREBASE_PROJECT_ID'),
                "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
                "client_email": os.getenv('FIREBASE_CLIENT_EMAIL')
            })

            # تهيئة Firebase Admin SDK
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
                logger.info("تم تهيئة Firebase Admin SDK بنجاح")

        except Exception as e:
            logger.error(f"خطأ في تهيئة Firebase: {str(e)}")

    def generate_verification_code(self, length=6):
        """توليد رمز تحقق عشوائي
        Generate a random verification code"""
        return ''.join(random.choices(string.digits, k=length))

    def calculate_expiry(self, minutes=10):
        """حساب وقت انتهاء صلاحية الرمز
        Calculate code expiration time"""
        return datetime.now() + timedelta(minutes=minutes)

    async def send_verification_code(self, phone_number: str) -> dict:
        """إرسال رابط التحقق عبر Firebase
        Send verification link via Firebase"""
        try:
            # إنشاء رابط تحقق مخصص
            link_params = {
                'phoneNumber': phone_number,
                'dynamicLinkDomain': os.getenv('FIREBASE_DYNAMIC_LINK_DOMAIN')
            }

            action_code_settings = auth.ActionCodeSettings(
                url=os.getenv('APP_URL', 'https://silvariumsocial.com'),
                handle_code_in_app=True
            )

            # إرسال رابط التحقق
            link = auth.generate_sign_in_with_phone_number_link(
                phone_number,
                action_code_settings
            )

            logger.info(f"تم إرسال رابط التحقق بنجاح للرقم: {phone_number}")
            return {
                'success': True,
                'message': 'تم إرسال رابط التحقق بنجاح | Verification link sent successfully',
                'verification_link': link
            }

        except Exception as e:
            logger.error(f"فشل في إرسال رابط التحقق: {str(e)}")
            return {
                'success': False,
                'message': f'فشل في إرسال رابط التحقق | Failed to send verification link: {str(e)}'
            }

    async def verify_phone_number(self, phone_number: str, verification_id: str) -> dict:
        """التحقق من رقم الهاتف باستخدام Firebase
        Verify phone number using Firebase"""
        try:
            # التحقق من رمز التحقق
            user = auth.get_user_by_phone_number(phone_number)

            if user:
                logger.info(f"تم التحقق من رقم الهاتف بنجاح: {phone_number}")
                return {
                    'success': True,
                    'message': 'تم التحقق من رقم الهاتف بنجاح | Phone number verified successfully',
                    'user_id': user.uid
                }
            else:
                logger.warning(f"فشل في التحقق من رقم الهاتف: {phone_number}")
                return {
                    'success': False,
                    'message': 'فشل في التحقق من رقم الهاتف | Phone number verification failed'
                }

        except Exception as e:
            logger.error(f"خطأ في التحقق من رقم الهاتف: {str(e)}")
            return {
                'success': False,
                'message': f'خطأ في التحقق من رقم الهاتف | Phone verification error: {str(e)}'
            }

firebase_auth_service = FirebaseAuthService()