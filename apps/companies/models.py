import uuid
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.accounts.models import Role

class Company(SoftDeleteModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_companies'
    )
    max_users = models.PositiveIntegerField(default=50)
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class Team(TimeStampedModel):
    name = models.CharField(max_length=200)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='teams')
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='managed_teams'
    )

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Invitation(TimeStampedModel):
    email = models.EmailField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    is_accepted = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Invite for {self.email} to {self.company.name}"
