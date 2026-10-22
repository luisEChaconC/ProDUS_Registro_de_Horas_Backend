from django.contrib import admin

from .models import Request


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'assistant', 'admin', 'request_type', 'created_at', 'is_attended')
    list_filter = ('request_type', 'is_attended')
    search_fields = ('assistant__username', 'assistant__full_name', 'message')
