
from datetime import datetime

import jwt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

from .crud_deps import crud_actions
from .models import BlacklistedToken


def decode_token(raw_token: str) -> dict:
    try:
        return jwt.decode(
            raw_token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationFailed("Invalid token")


def blacklist_token(raw_token: str):
    decoded = decode_token(raw_token)
    jti = decoded.get("jti")

    if not jti:
        raise Exception("Token has no jti")

    crud_actions.get_or_create(BlacklistedToken, token=jti)


def is_token_blacklisted(raw_token: str) -> bool:
    try:
        decoded = jwt.decode(
            raw_token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": False},  
        )
        jti = decoded.get("jti")
        return crud_actions.exists(BlacklistedToken, token=jti)
    except Exception:
        return True  
def delete_expired_blacklisted_tokens(cutoff: datetime):
    return crud_actions.delete(BlacklistedToken, blacklisted_on__lt=cutoff)