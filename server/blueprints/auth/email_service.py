"""Email Service for authentication"""
import os
import logging
from datetime import datetime, timedelta
import psycopg2
from typing import Tuple, Optional
import random
import string
from flask_mail import Mail, Message
from flask import current_app

logger = logging.getLogger('silvarium_auth')

class EmailService:
    def __init__(self):
        """Initialize Email Service"""
        self.max_attempts = int(os.getenv('EMAIL_MAX_ATTEMPTS', '5'))
        self.code_expiry = int(os.getenv('EMAIL_CODE_EXPIRY', '600'))  # 10 minutes
        self.mail = None

    def init_mail(self, app):
        """Initialize Flask-Mail with app context"""
        app.config.update(
            MAIL_SERVER='smtp.gmail.com',
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
            MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
            MAIL_DEFAULT_SENDER=os.getenv('MAIL_DEFAULT_SENDER')
        )
        self.mail = Mail(app)
        logger.info("تم تهيئة خدمة البريد الإلكتروني")

    def generate_verification_code(self) -> str:
        """Generate a 4-digit verification code | توليد رمز تحقق من 4 أرقام"""
        return ''.join(random.choices(string.digits, k=4))

    def validate_email(self, email: str) -> bool:
        """Validate email format | التحقق من صيغة البريد الإلكتروني"""
        from email_validator import validate_email as validator, EmailNotValidError
        try:
            validator(email)
            return True
        except EmailNotValidError:
            return False

    async def send_verification_code(self, email: str) -> Tuple[bool, Optional[str]]:
        """Send verification code via email"""
        try:
            if not self.validate_email(email):
                return False, "عنوان البريد الإلكتروني غير صحيح"

            verification_code = self.generate_verification_code()
            logger.info(f"تم توليد رمز التحقق للبريد: {email}")

            # Send verification email
            msg = Message(
                'رمز التحقق من Silvarium',
                recipients=[email]
            )
            msg.body = f"""
            مرحباً،

            رمز التحقق الخاص بك هو: {verification_code}

            هذا الرمز صالح لمدة 10 دقائق.

            تحياتنا،
            فريق Silvarium
            """
            msg.html = f"""
            <div dir="rtl" style="text-align: right;">
                <h2>مرحباً،</h2>
                <p>رمز التحقق الخاص بك هو:</p>
                <h1 style="color: #4a5568; background: #edf2f7; padding: 10px; text-align: center; font-size: 32px;">
                    {verification_code}
                </h1>
                <p>هذا الرمز صالح لمدة 10 دقائق.</p>
                <br>
                <p>تحياتنا،<br>فريق Silvarium</p>
            </div>
            """

            if self.mail:
                self.mail.send(msg)
                logger.info(f"تم إرسال رمز التحقق إلى البريد الإلكتروني: {email}")

                # Save the code in database
                conn = psycopg2.connect(os.getenv('DATABASE_URL'))
                cur = conn.cursor()

                expires_at = datetime.now() + timedelta(minutes=10)
                cur.execute("""
                    UPDATE users 
                    SET verification_code = %s,
                        verification_code_expires_at = %s
                    WHERE email = %s
                """, (verification_code, expires_at, email))

                if cur.rowcount == 0:
                    # If no user exists with this email, create a temporary one
                    temp_username = f"temp_{email}_{int(datetime.now().timestamp())}"
                    cur.execute("""
                        INSERT INTO users (username, email, verification_code, verification_code_expires_at, status)
                        VALUES (%s, %s, %s, %s, 'pending')
                    """, (temp_username, email, verification_code, expires_at))

                conn.commit()
                cur.close()
                conn.close()

                return True, None
            else:
                logger.error("خدمة البريد الإلكتروني غير مهيأة")
                return False, "خدمة البريد الإلكتروني غير متاحة"

        except Exception as e:
            logger.error(f"خطأ في إرسال البريد الإلكتروني: {str(e)}")
            return False, str(e)

    async def check_rate_limit(self, email: str) -> bool:
        """Check if email has exceeded rate limit"""
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            # Get number of attempts in the last hour
            cur.execute("""
                SELECT COUNT(*) 
                FROM verification_attempts 
                WHERE email = %s 
                AND attempt_time > NOW() - INTERVAL '1 hour'
            """, (email,))

            count = cur.fetchone()[0] if cur.fetchone() else 0

            # Insert new attempt
            cur.execute("""
                INSERT INTO verification_attempts (email, attempt_time)
                VALUES (%s, NOW())
            """, (email,))

            conn.commit()
            cur.close()
            conn.close()

            return count < self.max_attempts

        except Exception as e:
            logger.error(f"خطأ في التحقق من حد الإرسال: {str(e)}")
            return False

    async def verify_code(self, email: str, code: str) -> Tuple[bool, Optional[str]]:
        """Verify email code"""
        try:
            if len(code) != 4 or not code.isdigit():
                return False, "رمز التحقق يجب أن يكون 4 أرقام"

            if not self.validate_email(email):
                return False, "عنوان البريد الإلكتروني غير صحيح"

            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cur = conn.cursor()

            cur.execute("""
                SELECT verification_code, verification_code_expires_at
                FROM users
                WHERE email = %s
            """, (email,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if not result:
                return False, "البريد الإلكتروني غير مسجل"

            stored_code, expires_at = result

            if datetime.now() > expires_at:
                return False, "انتهت صلاحية الرمز"

            if code != stored_code:
                return False, "رمز التحقق غير صحيح"

            return True, None

        except Exception as e:
            logger.error(f"خطأ في التحقق من الرمز: {str(e)}")
            return False, str(e)

# Initialize Email Service
email_service = EmailService()