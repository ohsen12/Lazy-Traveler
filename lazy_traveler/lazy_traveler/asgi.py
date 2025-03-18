import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from chatbot.routing import websocket_urlpatterns
from chatbot.middleware import JWTAuthMiddleware  # noqa: E402

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lazy_traveler.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': JWTAuthMiddleware(
        inner=URLRouter(
            websocket_urlpatterns
        )
    ),
})
