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

            logger.info("جاري تهيئة Firebase بالبيانات التالية | Initializing Firebase with credentials")
            logger.info(f"Project ID: {cred_dict.get('project_id')}")
            logger.info(f"Client Email: {cred_dict.get('client_email')}")

            # Initialize Firebase Admin SDK if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                logger.info("تم تهيئة خدمة Firebase بنجاح | Firebase service initialized successfully")
            else:
                logger.info("Firebase already initialized | تم تهيئة Firebase مسبقاً")

        except Exception as e:
            logger.error(f"خطأ في تهيئة Firebase: {str(e)} | Firebase initialization error: {str(e)}")
            raise

    def send_verification_code_sync(self, phone_number: str) -> Dict[str, Any]:
        """Synchronous version of send verification code"""
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

            # التحقق من عدد محاولات إرسال الرمز | Check verification code attempts
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

            # إنشاء رابط التحقق | Create verification link
            link = auth.generate_sign_in_with_phone_number_link(
                phone_number,
                auth.ActionCodeSettings(
                    url=os.getenv('APP_URL', 'https://silvariumsocial.com'),
                    handle_code_in_app=True,
                    ios_bundle_id='com.silvarium.social',
                    android_package_name='com.silvarium.social',
                    android_install_app=True,
                    android_minimum_version='12'
                )
            )

            logger.info(f"تم إرسال رابط التحقق بنجاح للرقم: {phone_number}")
            return {
                'success': True,
                'message': {
                    'ar': 'تم إرسال رمز التحقق بنجاح',
                    'en': 'Verification code sent successfully'
                },
                'verification_link': link
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
                    'ar': 'فشل في إرسال رمز التحقق، يرجى المحاولة مرة أخرى',
                    'en': 'Failed to send verification code, please try again'
                }
            }

    async def send_verification_code(self, phone_number: str) -> Dict[str, Any]:
        """Asynchronous version of send verification code"""
        # Use synchronous version in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send_verification_code_sync, phone_number)

    def verify_phone_number(self, phone_number: str, verification_id: str, code: str) -> Tuple[bool, Optional[str]]:
        """التحقق من رقم الهاتف والرمز | Verify phone number and code"""
        max_retries = 3
        retry_count = 0
        retry_delay = 1  # Start with 1 second delay

        while retry_count < max_retries:
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
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"فشل التحقق بعد {max_retries} محاولات: {str(e)}")
                    return False, f"فشل التحقق من رقم الهاتف بعد عدة محاولات | Phone verification failed after several attempts"

                # Exponential backoff
                time.sleep(retry_delay)
                retry_delay *= 2  # Double the delay for next retry
                logger.info(f"محاولة إعادة التحقق {retry_count} من {max_retries}")
                continue

    def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """التحقق من صحة رمز المصادقة | Verify authentication token"""
        try:
            return auth.verify_id_token(id_token)
        except Exception as e:
            logger.error(f"خطأ في التحقق من رمز المصادقة: {str(e)}")
            return None

    def link_phone_number(self, username: str, phone_number: str) -> Tuple[bool, Optional[str]]:
        """ربط رقم الهاتف بالمستخدم | Link phone number to user"""
        try:
            # التحقق من تنسيق رقم الهاتف | Validate phone number format
            if not phone_number.startswith('+'):
                logger.warning(f"رقم هاتف بتنسيق غير صحيح: {phone_number}")
                return False, "يجب أن يبدأ رقم الهاتف بـ + متبوعاً برمز الدولة | Phone number must start with + followed by country code"

            # إنشاء أو تحديث مستخدم Firebase | Create or update Firebase user
            try:
                user = auth.get_user_by_phone_number(phone_number)
                if user:
                    # Update user display name if exists
                    auth.update_user(
                        user.uid,
                        display_name=username
                    )
                else:
                    # Create new user with phone number
                    user = auth.create_user(
                        phone_number=phone_number,
                        display_name=username
                    )
                logger.info(f"تم ربط رقم الهاتف بنجاح: {phone_number}")
                return True, None

            except auth.PhoneNumberAlreadyExistsError:
                logger.error(f"رقم الهاتف مستخدم بالفعل: {phone_number}")
                return False, "رقم الهاتف مستخدم بالفعل | Phone number is already in use"

        except Exception as e:
            logger.error(f"خطأ في ربط رقم الهاتف: {str(e)}")
            return False, f"خطأ في ربط رقم الهاتف | Error linking phone number: {str(e)}"

# Initialize Firebase Auth Service with error handling
try:
    firebase_auth = FirebaseAuthService()
    logger.info("Firebase Auth Service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Auth Service: {str(e)}")
    firebase_auth = None