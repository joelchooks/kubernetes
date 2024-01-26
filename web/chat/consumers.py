from asgiref.sync import async_to_sync
from django.core.exceptions import ObjectDoesNotExist
from channels.generic.websocket import JsonWebsocketConsumer
from chat.models import *
from chat.serializers import MessageSerializer
from uuid import UUID
import json

def check_ws_authentication(user):
    """
    Check if the user is authenticated.

    Args:
        user: The user object.

    Returns:
        bool: True if the user is authenticated, False otherwise.
    """
    return isinstance(user, User)

class UUIDEncoder(json.JSONEncoder):
    """
    JSON encoder for UUID objects.
    """
    def default(self, obj):
        if isinstance(obj, UUID):
            return obj.hex
        return json.JSONEncoder.default(self, obj)

class ChatConsumer(JsonWebsocketConsumer):
    """
    WebSocket consumer for handling real-time chat messages and notifications.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.conversation_name = None
        self.conversation = None

    def connect(self):
        """
        Handles the WebSocket connection.
        If the user is not authenticated, the connection is not established.
        """
        self.user = self.scope["user"]
        if not check_ws_authentication(self.user):
            self.close()
            return

        print("Connected!")
        self.room_name = "home"
        self.accept()

        try:
            slug_qs = self.scope['url_route']['kwargs']
            slug1 = slug_qs.get('slug1')
            slug2 = slug_qs.get('slug2')
            if not slug1 or not slug2:
                self.send_json({
                    "error": "Invalid request",
                    "detail": "Missing or empty 'slug1' and 'slug2' parameters."
                })
                self.close()
                return

            self.conversation_name = f"{slug1}__{slug2}"

            sender = self.get_receiver(who=0)
            receiver = self.get_receiver(who=1)

        except Exception as err:
            self.send_json({
                "error": "Invalid request",
                "detail": "One of the slug user does not exist" if err == "51" else "invalid slugs"
            })
            self.close()
    

        try:
            self.conversation, created = Conversation.objects.get_or_create(name=self.conversation_name)

            async_to_sync(self.channel_layer.group_add)(
                self.conversation_name,
                self.channel_name,
            )
        except KeyError:
            self.send_json({
                "error": "Invalid request",
                "detail": "Missing 'slug' parameter."
            })
            self.close()
        except ObjectDoesNotExist:
            self.send_json({
                "error": "Invalid request",
                "detail": "Conversation does not exist."
            })
            self.close()
        except:
            self.send_json({
                "error": "Invalid request",
                "detail": "unknown error"
            })
            self.close()


        self.send_online_user_list()
        self.send_user_join_message()
        self.add_user_to_online_users()
        self.send_last_50_messages()

    def send_online_user_list(self):
        """
        Sends the list of online users in the conversation to the current user.
        """
        online_users = self.conversation.online.values_list('username', flat=True)
        self.send_json({
            "type": "online_user_list",
            "users": list(online_users),
        })

    def send_user_join_message(self):
        """
        Sends a user join message to the conversation group.
        """
        async_to_sync(self.channel_layer.group_send)(
            self.conversation_name,
            {
                "type": "user_join",
                "user": self.user.username,
            },
        )

    def add_user_to_online_users(self):
        """
        Adds the current user to the list of online users in the conversation.
        """
        self.conversation.join(self.user)

    def send_last_50_messages(self):
        """
        Sends the last 50 messages in the conversation to the current user.
        """
        messages = self.conversation.messages.all().order_by("-date_created")[:50]
        message_count = self.conversation.messages.all().count()
        self.send_json({
            "type": "last_50_messages",
            "messages": MessageSerializer(messages, many=True).data,
            "has_more": message_count > 50,
        })

    def disconnect(self, code):
        if check_ws_authentication(self.user):
            # Send the leave event to the conversation group
            async_to_sync(self.channel_layer.group_send)(
                self.conversation_name,
                {
                    "type": "user_leave",
                    "user": self.user.username,
                },
            )
            self.conversation.leave(self.user)

        return super().disconnect(code)

    def get_receiver(self, who: int):
        """
        Gets the user who is either the sender or the receiver depending on the parameter 'who' of the message.

        Returns:
            User: The user is the sender/receiver.
        """
        try:
            users_id = self.conversation_name.split("__")
            reciever_id = users_id[who]

            return User.objects.get(username=reciever_id)
        except ObjectDoesNotExist:
            raise Exception("51")
        except:
            raise Exception("99")



    def receive_json(self, content, **kwargs):
        message_type = content["type"]

        if message_type == "chat_message":
            try:
                message_receiver = self.get_receiver(who=1)

                message = Message.objects.create(
                    from_user=self.user,
                    to_user=message_receiver,
                    content=content["message"],
                    conversation=self.conversation
                )

                async_to_sync(self.channel_layer.group_send)(
                    self.conversation_name,
                    {
                        "type": "chat_message_echo",
                        "name": content["name"],
                        "message": MessageSerializer(message).data,
                    },
                )

                notification_group_name = message_receiver.username + "__notifications"
                async_to_sync(self.channel_layer.group_send)(
                    notification_group_name,
                    {
                        "type": "new_message_notification",
                        "name": self.user.id,
                        "message": MessageSerializer(message).data,
                    },
                )

                self.send_online_user_list()
                self.send_last_50_messages()

            except:
                self.send_json({
                    "error": "Invalid request",
                    "detail": "An error occured."
                })
                self.close()


        if message_type == "typing":
            async_to_sync(self.channel_layer.group_send)(
                self.conversation_name,
                {
                    "type": "typing",
                    "user": self.user.username,
                    "typing": content["typing"],
                },
            )

        if message_type == "read_messages":
            messages_to_me = self.conversation.messages.filter(to_user=self.user)
            messages_to_me.update(read=True)

            # Update the unread message count
            unread_count = Message.objects.filter(to_user=self.user, read=False).count()
            async_to_sync(self.channel_layer.group_send)(
                self.user.id + "__notifications",
                {
                    "type": "unread_count",
                    "unread_count": unread_count,
                },
            )
        return super().receive_json(content, **kwargs)

    def chat_message_echo(self, event):
        self.send_json(event)

    def user_join(self, event):
        self.send_json(event)

    def user_leave(self, event):
        self.send_json(event)

    def typing(self, event):
        self.send_json(event)

    def new_message_notification(self, event):
        self.send_json(event)

    def unread_count(self, event):
        self.send_json(event)

    @classmethod
    def encode_json(cls, content):
        return json.dumps(content, cls=UUIDEncoder)


class NotificationConsumer(JsonWebsocketConsumer):
    """
    WebSocket consumer for handling real-time notifications.
    This consumer handles private notifications for authenticated users.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.notification_group_name = None

    def connect(self):
        """
        Handles the WebSocket connection.
        If the user is not authenticated, the connection is not established.
        """
        self.user = self.scope["user"]
        if not check_ws_authentication(self.user):
            self.close()
            return

        self.accept()

        # Create a private notification group for the user
        self.notification_group_name = self.user.username + "__notifications"
        async_to_sync(self.channel_layer.group_add)(
            self.notification_group_name,
            self.channel_name,
        )

        # Send the count of unread messages to the user
        unread_count = Message.objects.filter(to_user=self.user, read=False).count()
        self.send_json(
            {
                "type": "unread_count",
                "unread_count": unread_count,
            }
        )

    def disconnect(self, code):
        """
        Handles the WebSocket disconnection.
        Removes the user from the private notification group.
        """
        if check_ws_authentication(self.user):
            async_to_sync(self.channel_layer.group_discard)(
                self.notification_group_name,
                self.channel_name,
            )
            
        return super().disconnect(code)

    def new_message_notification(self, event):
        """
        Handles a new message notification event and sends it to the user.
        """
        self.send_json(event)

    def unread_count(self, event):
        """
        Handles an unread message count event and sends it to the user.
        """
        self.send_json(event)
