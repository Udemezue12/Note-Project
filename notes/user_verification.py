

from django.contrib.auth import get_user_model
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from redis.client import Redis


from .crud_deps import CRUDDependencies, ExistingDependencies
from .env import (
    REDIS_URL,
    RESET_PASSWORD_SALT,
    RESET_SECRET_KEY,
    VERIFY_EMAIL_SALT,
    VERIFY_EMAIL_SECRET_KEY
)


User = get_user_model()
reset_serializer = URLSafeTimedSerializer(RESET_SECRET_KEY or "")
verify_serializer = URLSafeTimedSerializer(VERIFY_EMAIL_SECRET_KEY or "")
resend_tracker: dict[str, dict] = {}
redis = Redis.from_url(REDIS_URL, decode_responses=True)


class UserVerification:
    def __init__(self):
        self.crud_actions = CRUDDependencies()
        self.check = ExistingDependencies()

    def verify_reset_token(
        self, token: str, expiration: int = 3600
    ) -> str | None:
        try:
            email = reset_serializer.loads(
                token, salt=RESET_PASSWORD_SALT, max_age=expiration
            )
            return email
        except (SignatureExpired, BadSignature):
            return None

    def verify_verify_token(
        self, token: str, expiration: int = 3600
    ) -> str | None:
        try:
            email = verify_serializer.loads(
                token, salt=VERIFY_EMAIL_SALT, max_age=expiration
            )
            return email
        except (SignatureExpired, BadSignature):
            return None
    def _decode(self,value):
     return value.decode() if isinstance(value, bytes) else value
    from typing import Optional

    def verify_otp(self, otp: str) -> Optional[str]:
        for key in redis.scan_iter(match="otp:*"):
            stored = redis.get(key)

            if stored and self._decode(stored) == otp:
                redis.delete(key)
                return self._decode(key).split(":")[1]

        return None


user_verify = UserVerification()
