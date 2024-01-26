from rest_framework import serializers
 
from .models import *


class UserDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        exclude = [
            "updated_at",
            "is_superuser",
            "groups",
            "user_permissions",
            "password",
        ]
 
 
class ConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
 
    class Meta:
        model = Conversation
        fields = ("id", "conv_id", "name", "other_user", "last_message")
 
    def get_last_message(self, obj):
        messages = obj.messages.all().order_by("-date_created")
        if not messages.exists():
            return None
        message = messages[0]
        return MessageSerializer(message).data
 
    def get_other_user(self, obj):
        usernames = obj.name.split("__")
        context = {}
        for username in usernames:
            if username != self.context["user"].username:
                # This is the other participant
                other_user = User.objects.get(username=username)
                return UserDetailSerializer(other_user, context=context).data
 
 
class MessageSerializer(serializers.ModelSerializer):
    from_user = serializers.SerializerMethodField()
    to_user = serializers.SerializerMethodField()
    conversation = serializers.SerializerMethodField()
 
    class Meta:
        model = Message
        fields = (
            "message_id",
            "conversation",
            "from_user",
            "to_user",
            "content",
            "date_created",
            "read",
        )
 
    def get_conversation(self, obj: Message):
        return str(obj.conversation.conv_id)
 
    def get_from_user(self, obj: Message):
        return UserDetailSerializer(obj.from_user).data
 
    def get_to_user(self, obj: Message):
        return UserDetailSerializer(obj.to_user).data
    

