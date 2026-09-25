import os
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

SECRET_KEY = os.getenv("SECRET_KEY", "lucas-garage-crypto-salt-2026")
SECURITY_SALT = "booking-email-verification-salt"

serializer = URLSafeTimedSerializer(SECRET_KEY)

def generate_verification_token(booking_dict):
    """
    Packs booking details into a signed URL-safe string.
    """
    return serializer.dumps(booking_dict, salt=SECURITY_SALT)

def verify_booking_token(token, max_age_seconds=1800):
    """
    Decodes and validates token. Rejects expired (>30m) or forged tokens.
    Returns: (is_valid: bool, data_dict_or_error_message: dict | str)
    """
    try:
        data = serializer.loads(token, salt=SECURITY_SALT, max_age=max_age_seconds)
        return True, data
    except SignatureExpired:
        return False, "This booking confirmation link has expired (valid for 30 minutes). Please choose your slot again."
    except BadSignature:
        return False, "Invalid or corrupted booking verification link."
