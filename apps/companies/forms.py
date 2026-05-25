from django import forms
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Role

from .models import Company, Invitation, Team


class CompanyCreateForm(forms.ModelForm):
    """Create a company when the user (admin/manager) has none assigned yet."""

    team_names = forms.CharField(
        label=_("Teams"),
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-input",
                "rows": 4,
                "placeholder": "Engineering\nSales\nHR",
            }
        ),
        help_text=_("One team per line or comma-separated. Optional."),
    )

    class Meta:
        model = Company
        fields = ["name", "max_users"]
        labels = {
            "name": _("Company name"),
            "max_users": _("Max users"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": _("Acme Corp")}),
            "max_users": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["max_users"].initial = 50

    def clean(self):
        cleaned_data = super().clean()
        from .services import company_service

        cleaned_data["parsed_teams"] = company_service.parse_team_names(
            cleaned_data.get("team_names") or ""
        )
        return cleaned_data


class TeamCreateForm(forms.ModelForm):
    """Add a single team to an existing company."""

    class Meta:
        model = Team
        fields = ["name"]
        labels = {"name": _("Team name")}
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": _("Engineering")}
            ),
        }

    def __init__(self, *args, company: Company | None = None, **kwargs):
        self.company = company
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError(_("Team name cannot be empty."))
        if (
            self.company
            and Team.objects.filter(company=self.company, name__iexact=name).exists()
        ):
            raise forms.ValidationError(_("A team with this name already exists."))
        return name

    def save(self, commit=True):
        team = super().save(commit=False)
        team.company = self.company
        if commit:
            team.save()
        return team


class CompanyUpdateForm(forms.ModelForm):
    """
    Form for updating company settings (name, max_users, feature flags).
    The slug is intentionally excluded — it is set once on creation.
    """

    class Meta:
        model = Company
        fields = ["name", "max_users", "is_active"]
        labels = {
            "name": _("Company name"),
            "max_users": _("Max users"),
            "is_active": _("Active"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": _("Acme Corp")}),
            "max_users": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
        }


class InviteUserForm(forms.Form):
    """
    Form for a manager to invite a new member to the team.
    """

    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(
            attrs={"class": "form-input", "placeholder": "employee@example.com"}
        ),
    )
    role = forms.ChoiceField(
        label=_("Role"),
        choices=Role.choices,
        initial=Role.EMPLOYEE,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    team = forms.ModelChoiceField(
        label=_("Team (optional)"),
        queryset=Team.objects.none(),
        required=False,
        empty_label=_("No specific team"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, company: Company | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields["team"].queryset = Team.objects.filter(company=company)


class UpdateMemberRoleForm(forms.Form):
    """Minimal form used by the HTMX endpoint to change a member's role."""

    role = forms.ChoiceField(
        choices=Role.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
