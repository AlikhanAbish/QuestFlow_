from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class LoginForm(AuthenticationForm):
    """
    HTMX-compatible login form.
    AuthenticationForm already provides username/password fields and validation.
    """
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'id': 'login-email',
            'placeholder': 'your@email.com',
            'autofocus': True,
            'class': 'form-input',
        }),
        label=_('Email'),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'id': 'login-password',
            'placeholder': '••••••••',
            'class': 'form-input',
        }),
        label=_('Password'),
    )


class RegistrationForm(forms.ModelForm):
    """
    Registration form that expects an invitation token to be validated externally.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'id': 'reg-password',
            'placeholder': '••••••••',
            'class': 'form-input',
        }),
        label=_('Password'),
        min_length=8,
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'id': 'reg-password-confirm',
            'placeholder': '••••••••',
            'class': 'form-input',
        }),
        label=_('Confirm password'),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'id': 'reg-username', 'class': 'form-input', 'placeholder': 'john_doe'}),
            'first_name': forms.TextInput(attrs={'id': 'reg-first-name', 'class': 'form-input', 'placeholder': 'John'}),
            'last_name': forms.TextInput(attrs={'id': 'reg-last-name', 'class': 'form-input', 'placeholder': 'Doe'}),
            'email': forms.EmailInput(attrs={'id': 'reg-email', 'class': 'form-input', 'placeholder': 'your@email.com', 'readonly': True}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError(_('Passwords do not match.'))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for users to update their basic profile settings.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'id': 'profile-first-name', 'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'id': 'profile-last-name', 'class': 'form-input'}),
            'username': forms.TextInput(attrs={'id': 'profile-username', 'class': 'form-input'}),
            'avatar': forms.ClearableFileInput(attrs={'id': 'profile-avatar', 'class': 'form-file-input'}),
        }
