from django.contrib import admin

from import_export import resources
from import_export.admin import ImportExportModelAdmin

from chat.models import *

###############################################################################
# RESOURCES
class UserResource(resources.ModelResource):
    class Meta:
        model = User

class ConversationResource(resources.ModelResource):
    class Meta:
        model = Conversation


class MessageResource(resources.ModelResource):
    class Meta:
        model = Message



#######################################################################
# RESOURCE ADMINS
        

class UserResourceAdmin(ImportExportModelAdmin):
    search_fields = ['email']
    resource_class = UserResource
    list_filter = (
        ("date_joined", "is_suspended")
    )
    readonly_fields = ['password']
    date_hierarchy = 'date_joined'

    def get_list_display(self, request):
        return [field.name for field in self.model._meta.concrete_fields]
    

class ConversationResourceAdmin(ImportExportModelAdmin):
    search_fields = ['id', 'name']
    resource_class = ConversationResource
    list_filter = (
        ('date_created',)
    )
    date_hierarchy = 'date_created'

    def get_list_display(self, request):
        return [field.name for field in self.model._meta.concrete_fields]
    

class MessageResourceAdmin(ImportExportModelAdmin):
    search_fields = ['message_id', 'from_user__email', 'to_user__email']
    resource_class = MessageResource
    list_filter = (
        ('date_created', 'to_user')
    )
    date_hierarchy = 'date_created'

    def get_list_display(self, request):
        return [field.name for field in self.model._meta.concrete_fields]




admin.site.register(User, UserResourceAdmin)
admin.site.register(Conversation, ConversationResourceAdmin)
admin.site.register(Message, MessageResourceAdmin)






