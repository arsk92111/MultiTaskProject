from django.urls import path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/chat/live_chatboot/', ChatConsumer.as_asgi()),
]