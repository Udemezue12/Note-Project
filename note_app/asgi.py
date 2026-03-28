import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "note_app.settings")


from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()


from channels.routing import ProtocolTypeRouter, URLRouter
from notes.websockets_urls import websocket_urlpatterns
from notes.middleware.websocket_jwt_auth import JWTAuthMiddleware  


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,

        "websocket": JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        ),
    }
)