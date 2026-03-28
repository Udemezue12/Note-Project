
from urllib.parse import parse_qs

import jwt
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth import get_user_model

from ..auth_utils import is_token_blacklisted
from ..crud_deps import crud_actions
from ..env import ENV

User = get_user_model()


@database_sync_to_async
def get_user(user_id):
    return crud_actions.get_object(User, id=user_id)


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        headers = dict(scope["headers"])

        cookies = {}
        if b"cookie" in headers:
            cookie_str = headers[b"cookie"].decode()
            for item in cookie_str.split(";"):
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    cookies[key] = value

        token = cookies.get("access_token")
        if ENV == "production" and not token:
            print("No token provided in production")
            return await self.close_connection(send, 4001)

        if not token and ENV != "production":
            query_string = parse_qs(scope["query_string"].decode())
            token = query_string.get("token", [None])[0]

            if token:
                print("Using QUERY TOKEN (DEV ONLY)")

        scope["user"] = None

        if token:
            try:
                if await database_sync_to_async(is_token_blacklisted)(token):
                    print("BLACKLISTED TOKEN")
                    return await self.close_connection(send, 4003)

                decoded = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=["HS256"],
                )

                user = await get_user(decoded["user_id"])
                scope["user"] = user
            except jwt.ExpiredSignatureError:
                return await self.close_connection(send, 4002)
            except Exception as e:

                return await self.close_connection(send, 4003)

            return await super().__call__(scope, receive, send)

    async def close_connection(self, send, code):
        await send({
            "type": "websocket.close",
            "code": code
        })
