from django.urls import path
from chat.consumers import *
 
websocket_urlpatterns = [
    path("chat/<slug1>/<slug2>/", ChatConsumer.as_asgi()),
    path("notifications/", NotificationConsumer.as_asgi()),
]
