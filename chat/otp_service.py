"""OTP generation, storage, and optional EmailJS server-side sending."""
import random, string, requests, logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class OTPService:
    @staticmethod
    def generate_otp(length=6):
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def store_otp(email, otp, timeout=300):
        cache.set(f"otp:{email}", otp, timeout)
        logger.info(f"OTP stored for {email}")

    @staticmethod
    def verify_otp(email, user_otp):
        stored = cache.get(f"otp:{email}")
        if stored and stored == user_otp:
            cache.delete(f"otp:{email}")
            return True
        return False

    @staticmethod
    def send_otp_via_emailjs(email, otp):
        """Optional server-side EmailJS call (browser SDK is preferred)."""
        try:
            r = requests.post("https://api.emailjs.com/api/v1.0/email/send", json={
                "service_id":  settings.EMAILJS_SERVICE_ID,
                "template_id": settings.EMAILJS_TEMPLATE_ID,
                "user_id":     settings.EMAILJS_PUBLIC_KEY,
                "template_params": {"to_email": email, "otp_code": otp, "app_name": "Synapse AI"}
            })
            return r.status_code == 200
        except Exception as e:
            logger.error(f"EmailJS error: {e}")
            return False


otp_service = OTPService()
