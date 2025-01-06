"""SMS Service for authentication"""
import os
import logging
from datetime import datetime, timedelta
import psycopg2
from typing import Tuple, Optional
import random
import string

logger = logging.getLogger('silvarium_auth')

class SMSService:
    def __init__(self):
        """Initialize SMS Service"""
        self.max_attempts = int(os.getenv('SMS_MAX_ATTEMPTS', '5'))
        self.code_expiry = int(os.getenv('SMS_CODE_EXPIRY', '600'))  # 10 minutes

    def generate_verification_code(self) -> str:
        """Generate a 4-digit verification code | توليد رمز تحقق من 4 أرقام"""
        return ''.join(random.choices(string.digits, k=4))

    def validate_saudi_phone(self, phone_number: str) -> bool:
        """Validate Saudi phone number format | التحقق من صيغة رقم الهاتف السعودي"""
        # Remove spaces and dashes
        clean_number = phone_number.replace(' ', '').replace('-', '')
        # Must start with +966 followed by 9 digits
        return clean_number.startswith('+966') and len(clean_number) == 13 and clean_number[4:].isdigit()

    async def send_verification_code(self, phone_number: str) -> Tuple[bool, Optional[str]]:
        """Send verification code via SMS"""
        try:
            if not self.validate_saudi_phone(phone_number):
                return False, "رقم الهاتف غير صحيح. يجب أن يبدأ بـ +966 ويتكون من 13 رقم"

            verification_code = self.generate_verification_code()

            # For development, just log the code
            logger.info(f"رمز التحقق للرقم {phone_number}: {verification_code}")

            # Save the code in database
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            expires_at = datetime.now() + timedelta(minutes=10)
            cur.execute("""
                UPDATE users 
                SET verification_code = %s,
                    verification_code_expires_at = %s
                WHERE phone_number = %s
            """, (verification_code, expires_at, phone_number))

            if cur.rowcount == 0:
                # If no user exists with this phone number, create a temporary one
                temp_username = f"temp_{phone_number}_{int(datetime.now().timestamp())}"
                cur.execute("""
                    INSERT INTO users (username, phone_number, verification_code, verification_code_expires_at, status)
                    VALUES (%s, %s, %s, %s, 'pending')
                """, (temp_username, phone_number, verification_code, expires_at))

            conn.commit()
            cur.close()
            conn.close()

            return True, None

        except Exception as e:
            logger.error(f"خطأ في إرسال رسالة SMS: {str(e)}")
            return False, str(e)

    async def check_rate_limit(self, phone_number: str) -> bool:
        """Check if phone number has exceeded rate limit"""
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

            count = cur.fetchone()[0] if cur.fetchone() else 0

            # Insert new attempt
            cur.execute("""
                INSERT INTO verification_attempts (phone_number, attempt_time)
                VALUES (%s, NOW())
            """, (phone_number,))

            conn.commit()
            cur.close()
            conn.close()

            return count < self.max_attempts

        except Exception as e:
            logger.error(f"خطأ في التحقق من حد الإرسال: {str(e)}")
            return False

    async def verify_code(self, phone_number: str, code: str) -> Tuple[bool, Optional[str]]:
        """Verify SMS code"""
        try:
            if len(code) != 4 or not code.isdigit():
                return False, "رمز التحقق يجب أن يكون 4 أرقام"

            if not self.validate_saudi_phone(phone_number):
                return False, "رقم الهاتف غير صحيح"

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
                return False, "رقم الهاتف غير مسجل"

            stored_code, expires_at = result

            if datetime.now() > expires_at:
                return False, "انتهت صلاحية الرمز"

            if code != stored_code:
                return False, "رمز التحقق غير صحيح"

            return True, None

        except Exception as e:
            logger.error(f"خطأ في التحقق من الرمز: {str(e)}")
            return False, str(e)

# Initialize SMS Service
sms_service = SMSService()