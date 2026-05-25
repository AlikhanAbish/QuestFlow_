from django.contrib import admin
from .models import Notification, NotificationTemplate


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display    = ('recipient', 'type', 'title', 'is_read', 'created_at')
    list_filter     = ('type', 'is_read')
    search_fields   = ('recipient__email', 'title', 'body')
    readonly_fields = ('created_at', 'updated_at', 'metadata')
    ordering        = ('-created_at',)
    list_select_related = ('recipient',)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display  = ('name', 'type', 'is_active', 'created_at')
    list_filter   = ('type', 'is_active')
    search_fields = ('name', 'title_template', 'body_template')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'type', 'is_active'),
        }),
        ('Templates', {
            'fields': ('title_template', 'body_template', 'default_action_url'),
            'description': 'Use {variable} placeholders to inject dynamic values at send time.',
        }),
    )
