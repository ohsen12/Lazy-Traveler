import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lazy_traveler.settings")  # noqa: E402
django.setup()  # noqa: E402

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

from chatbot.middleware import JWTAuthMiddleware  # noqa: E402

django_asgi_app = get_asgi_application()

from chatbot.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTAuthMiddleware(
        inner=URLRouter(
            websocket_urlpatterns
        )
    ),
})
