"""
Django Admin — Synapse AI.
Enforces 10-user limit and provides chat session management.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib import messages as django_messages
from django.conf import settings
from .models import ChatSession, ChatMessage


class LimitedUserAdmin(UserAdmin):
    def save_model(self, request, obj, form, change):
        if not change:
            if User.objects.count() >= settings.MAX_USERS:
                django_messages.error(
                    request,
                    f"Cannot add more users. Maximum of {settings.MAX_USERS} users allowed."
                )
                return
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        if User.objects.count() >= settings.MAX_USERS:
            return False
        return super().has_add_permission(request)


admin.site.unregister(User)
admin.site.register(User, LimitedUserAdmin)


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'timestamp')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display   = ('user', 'title', 'created_at', 'updated_at', 'is_active')
    list_filter    = ('is_active', 'user')
    search_fields  = ('title', 'user__username')
    inlines        = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'short_content', 'timestamp')
    list_filter  = ('role',)

    def short_content(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    short_content.short_description = 'Content'


admin.site.site_header  = 'Synapse AI — Admin'
admin.site.site_title   = 'Synapse Admin'
admin.site.index_title  = 'Manage Users & Chat Sessions'
