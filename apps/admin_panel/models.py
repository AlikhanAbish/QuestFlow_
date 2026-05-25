from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel

class AuditLog(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.action} at {self.created_at}"

class SystemSetting(TimeStampedModel):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['key']

    def __str__(self):
        return self.key
