"""SMS Service for authentication"""
import os
import logging
from datetime import datetime, timedelta
import psycopg2
from typing import Tuple, Optional, Dict, Any
import aiohttp
import json

logger = logging.getLogger('silvarium_auth')

class SMSService:
    def __init__(self):
        """Initialize SMS Service"""
        self.api_url = os.getenv('SMS_API_URL', 'https://api.example.com/sms')  # Replace with actual SMS provider
        self.api_key = os.getenv('SMS_API_KEY', '')
        self.sender_id = os.getenv('SMS_SENDER_ID', 'Silvarium')
        self.max_attempts = int(os.getenv('SMS_MAX_ATTEMPTS', '5'))
        self.code_expiry = int(os.getenv('SMS_CODE_EXPIRY', '600'))  # 10 minutes

    async def send_verification_code(self, phone_number: str, code: str) -> Tuple[bool, Optional[str]]:
        """Send verification code via SMS"""
        try:
            # For development, just log the code
            logger.info(f"رمز التحقق للرقم {phone_number}: {code}")
            return True, None

            # In production, uncomment and configure with your SMS provider
            """
            async with aiohttp.ClientSession() as session:
                payload = {
                    'to': phone_number,
                    'message': f'رمز التحقق الخاص بك هو: {code}',
                    'sender': self.sender_id
                }
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        return True, None
                    error_data = await response.text()
                    return False, f"Error sending SMS: {error_data}"
            """

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

            count = cur.fetchone()[0]
            
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
