"""
ASGI config for chann_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from pathlib import Path
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chann_project.settings')
 
# This application object is used by any ASGI server configured to use this file.
django_application = get_asgi_application()
 
from . import routing
 
from channels.routing import ProtocolTypeRouter, URLRouter
 
 
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter(routing.websocket_urlpatterns),
    }
)