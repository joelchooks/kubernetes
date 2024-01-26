from django.urls import path
from chat.views import *

app_name = "chat"

chat = [
    path('conversations', ConversationViewSet.as_view(actions={'get': 'list'}), name="conversations"),
]


urlpatterns = [
    *chat,
]
