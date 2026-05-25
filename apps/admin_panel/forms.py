from django import forms
from apps.companies.models import Company
from apps.gamification.models import GamificationRule, Badge
from apps.accounts.models import User
from .models import SystemSetting

class CompanyCreationForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'slug', 'owner', 'max_users']

class UserRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['role']

class BadgeForm(forms.ModelForm):
    class Meta:
        model = Badge
        fields = ['name', 'description', 'icon', 'trigger_type', 'trigger_value']

class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = ['key', 'value', 'description']
