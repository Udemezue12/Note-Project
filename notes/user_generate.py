import secrets
from random import randint

from itsdangerous import URLSafeTimedSerializer
from redis.client import Redis

from .env import (
    REDIS_URL,
    RESET_PASSWORD_SALT,
    RESET_SECRET_KEY,
    VERIFY_EMAIL_SALT,
    VERIFY_EMAIL_SECRET_KEY,
)


reset_serializer = URLSafeTimedSerializer(RESET_SECRET_KEY)
verify_serializer = URLSafeTimedSerializer(VERIFY_EMAIL_SECRET_KEY)

redis = Redis.from_url(REDIS_URL, decode_responses=True)


class UserGenerate:

    async def generate_csrf_token(self) -> str:
        return secrets.token_hex(32)

    def generate_verify_token(self, email: str) -> str:
        return verify_serializer.dumps(email, salt=VERIFY_EMAIL_SALT)

    def generate_reset_token(self, email: str) -> str:
        return reset_serializer.dumps(email, salt=RESET_PASSWORD_SALT)

    def generate_otp(self, email: str) -> str:

        otp = str(randint(100000, 999999))
        setted = redis.setex(f"otp:{email}", 300, otp)
        print(f"otp:{otp}")
        print(f"Redis set:{setted}")
        return otp


user_generate = UserGenerate()
