from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.conf import settings

from chat.managers import UserManager

import os
import random
import string
import uuid
 
 

def profile_picture_upload_path(instance, filename):
    """
    Construct a dynamic path for profile picture
    """
    user_id = instance.id
    base_filename, file_extension = os.path.splitext(filename)
    
    return f'media/profile_pic/{user_id}/{base_filename}{file_extension}'


def validate_file_size(value):
    """
    Get the maximum file size from settings (in bytes)
    """
    max_size = getattr(settings, 'MAX_FILE_SIZE', 2 * 1024 * 1024)  # 2MB by default

    if value.size > max_size:
        raise ValidationError(f"The file size must not exceed {max_size} bytes.")
    

class User(AbstractUser):
    middle_name = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(unique=True)
    is_suspended = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to=profile_picture_upload_path, validators=[validate_file_size], blank=True, null=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    
    objects = UserManager()


 
class Conversation(models.Model):
    conv_id = models.UUIDField(default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    online = models.ManyToManyField(to=User, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
 
    def get_online_count(self):
        return self.online.count()
 
    def join(self, user):
        self.online.add(user)
        self.save()
 
    def leave(self, user):
        self.online.remove(user)
        self.save()
 
    def __str__(self):
        return f"{self.name} ({self.get_online_count()})"
 
 
class Message(models.Model):
    message_id = models.UUIDField(default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    from_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="messages_from_me"
    )
    to_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="messages_to_me"
    )
    content = models.CharField(max_length=512)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    read = models.BooleanField(default=False)
 
    def __str__(self):
        return f"From {self.from_user.email} to {self.to_user.email}: {self.content} [{self.date_created}]"