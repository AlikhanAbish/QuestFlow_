"""
Views for section 4.6 — Companies & Teams.

All mutation endpoints (POST) use HTMX and return partial HTML fragments.
GET views render full pages except where noted.

URL mapping (companies/urls.py):
    GET  /company/settings/                   → CompanySettingsView
    POST /company/settings/update/            → CompanyUpdateView
    GET  /team/members/                       → TeamMembersView
    POST /team/invite/                        → InviteUserView
    POST /team/invite/<id>/send/              → ResendInvitationView
    GET  /invite/<token>/                     → AcceptInviteView
    POST /team/members/<id>/role/             → UpdateMemberRoleView
    POST /team/members/<id>/remove/           → RemoveMemberView
"""
import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import View
from urllib.parse import urlencode

from apps.accounts.mixins import RoleRequiredMixin
from apps.accounts.models import Role

from .forms import (
    CompanyCreateForm,
    CompanyUpdateForm,
    InviteUserForm,
    TeamCreateForm,
    UpdateMemberRoleForm,
)
from .models import Company, Invitation, Team
from .services import (
    InvitationAlreadyAcceptedError,
    InvitationEmailError,
    InvitationExpiredError,
    InvitationNotFoundError,
    InvitationService,
    company_service,
)

logger = logging.getLogger(__name__)
User = get_user_model()

invitation_service = InvitationService()


def _user_company(user: User) -> Company | None:
    if not user.company_id:
        return None
    return Company.objects.filter(pk=user.company_id, is_active=True).first()


# ---------------------------------------------------------------------------
# Company Settings
# ---------------------------------------------------------------------------

class CompanySettingsView(RoleRequiredMixin, View):
    """GET /company/settings/ — full page with company details & pending invites."""

    required_roles = [Role.MANAGER, Role.ADMIN]
    template_name = "companies/company_settings.html"

    def get(self, request, *args, **kwargs):
        company = _user_company(request.user)
        if company is None:
            return TemplateResponse(request, self.template_name, {
                "company": None,
                "create_form": CompanyCreateForm(),
            })

        form = CompanyUpdateForm(instance=company)
        pending = invitation_service.get_pending_invitations(company)

        teams = Team.objects.filter(company=company).order_by("name")

        return TemplateResponse(request, self.template_name, {
            "company": company,
            "form": form,
            "teams": teams,
            "team_form": TeamCreateForm(company=company),
            "invite_form": InviteUserForm(company=company),
            "pending_invitations": pending,
        })


class CompanyCreateView(RoleRequiredMixin, View):
    """POST /company/create/ — create a company when the user has none yet."""

    required_roles = [Role.MANAGER, Role.ADMIN]

    def post(self, request, *args, **kwargs):
        if _user_company(request.user) is not None:
            messages.info(request, _("You already belong to a company."))
            return redirect("companies:company_settings")

        form = CompanyCreateForm(request.POST)
        if form.is_valid():
            team_names = form.cleaned_data["parsed_teams"]
            company = company_service.create_company(
                name=form.cleaned_data["name"],
                max_users=form.cleaned_data["max_users"],
                owner=request.user,
                team_names=team_names,
            )
            if team_names:
                messages.success(
                    request,
                    _(
                        "Company “%(name)s” created with %(count)d team(s). "
                        "You can now invite team members."
                    )
                    % {"name": company.name, "count": len(team_names)},
                )
            else:
                messages.success(
                    request,
                    _("Company “%(name)s” created. You can now invite team members.")
                    % {"name": company.name},
                )
            return redirect("companies:company_settings")

        messages.error(request, _("Please correct the errors below."))
        return TemplateResponse(
            request,
            CompanySettingsView.template_name,
            {"company": None, "create_form": form},
        )


class TeamCreateView(RoleRequiredMixin, View):
    """POST /company/teams/create/ — add a team to the current company."""

    required_roles = [Role.MANAGER, Role.ADMIN]

    def post(self, request, *args, **kwargs):
        company = _user_company(request.user)
        if company is None:
            messages.error(request, _("Create a company before adding teams."))
            return redirect("companies:company_settings")

        form = TeamCreateForm(request.POST, company=company)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                _("Team “%(name)s” created.") % {"name": form.cleaned_data["name"]},
            )
            return redirect("companies:company_settings")

        messages.error(request, _("Could not create team. Please check the name."))
        teams = Team.objects.filter(company=company).order_by("name")
        return TemplateResponse(
            request,
            CompanySettingsView.template_name,
            {
                "company": company,
                "form": CompanyUpdateForm(instance=company),
                "teams": teams,
                "team_form": form,
                "invite_form": InviteUserForm(company=company),
                "pending_invitations": invitation_service.get_pending_invitations(company),
            },
        )


class CompanyUpdateView(RoleRequiredMixin, View):
    """POST /company/settings/update/ — HTMX: update company settings."""

    required_roles = [Role.MANAGER, Role.ADMIN]

    def post(self, request, *args, **kwargs):
        company = _user_company(request.user)
        if company is None:
            messages.error(request, _("Create a company before updating settings."))
            return redirect("companies:company_settings")

        form = CompanyUpdateForm(request.POST, instance=company)

        if form.is_valid():
            form.save()
            messages.success(request, _("Company settings updated."))

            if request.htmx:
                return TemplateResponse(
                    request,
                    "companies/partials/_company_settings_form.html",
                    {"company": company, "form": form, "saved": True},
                )
            return redirect("companies:company_settings")

        if request.htmx:
            return TemplateResponse(
                request,
                "companies/partials/_company_settings_form.html",
                {"company": company, "form": form},
            )
        return redirect("companies:company_settings")


# ---------------------------------------------------------------------------
# Team Members
# ---------------------------------------------------------------------------

class TeamMembersView(RoleRequiredMixin, View):
    """GET /team/members/ — list of team members with management actions."""

    required_roles = [Role.MANAGER, Role.ADMIN]
    template_name = "companies/team_members.html"

    def get(self, request, *args, **kwargs):
        company = get_object_or_404(Company, pk=request.user.company_id, is_active=True)
        members = (
            User.objects.filter(company=company, is_active=True)
            .select_related("team")
            .order_by("last_name", "first_name")
        )
        invite_form = InviteUserForm(company=company)

        return TemplateResponse(request, self.template_name, {
            "company": company,
            "members": members,
            "invite_form": invite_form,
        })


class UpdateMemberRoleView(RoleRequiredMixin, View):
    """POST /team/members/<id>/role/ — HTMX: change a member's role."""

    required_roles = [Role.MANAGER, Role.ADMIN]

    def post(self, request, pk, *args, **kwargs):
        company = get_object_or_404(Company, pk=request.user.company_id, is_active=True)
        member = get_object_or_404(User, pk=pk, company=company)

        # Prevent demoting the only admin / yourself without caution
        if member == request.user:
            messages.warning(request, _("You cannot change your own role here."))
            if request.htmx:
                return TemplateResponse(
                    request,
                    "companies/partials/_member_row.html",
                    {"member": member, "error": _("Cannot change own role.")},
                )
            return redirect("companies:team_members")

        form = UpdateMemberRoleForm(request.POST)
        if form.is_valid():
            member.role = form.cleaned_data["role"]
            member.save(update_fields=["role"])
            logger.info(
                "User %s changed role of %s to %s",
                request.user.pk, member.pk, member.role,
            )

        if request.htmx:
            return TemplateResponse(
                request,
                "companies/partials/_member_row.html",
                {"member": member},
            )
        return redirect("companies:team_members")


class RemoveMemberView(RoleRequiredMixin, View):
    """POST /team/members/<id>/remove/ — HTMX: remove a member from the company."""

    required_roles = [Role.MANAGER, Role.ADMIN]

    def post(self, request, pk, *args, **kwargs):
        company = get_object_or_404(Company, pk=request.user.company_id, is_active=True)
        member = get_object_or_404(User, pk=pk, company=company)

        if member == request.user:
            messages.warning(request, _("You cannot remove yourself from the company."))
            if request.htmx:
                from django.http import HttpResponse
                return HttpResponse(status=204)
            return redirect("companies:team_members")

        # Detach from company — soft removal; account remains for audit history
        member.company = None
        member.team = None
        member.is_active = False
        member.save(update_fields=["company", "team", "is_active"])

        logger.info("User %s removed member %s from company %s", request.user.pk, pk, company.pk)

        if request.htmx:
            # Return empty string — HTMX swap removes the row
            from django.http import HttpResponse
            return HttpResponse("")
        return redirect("companies:team_members")


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------

class InviteUserView(RoleRequiredMixin, View):
    """POST /team/invite/ — send email invitation to a new member."""

    required_roles = [Role.MANAGER, Role.ADMIN]

    def post(self, request, *args, **kwargs):
        company = get_object_or_404(Company, pk=request.user.company_id, is_active=True)
        form = InviteUserForm(request.POST, company=company)

        if form.is_valid():
            base_url = request.build_absolute_uri("/").rstrip("/")
            email_sent = False
            status_error = None
            invite = None

            invite = invitation_service.create_invitation(
                email=form.cleaned_data["email"],
                company=company,
                invited_by=request.user,
                role=form.cleaned_data["role"],
                team=form.cleaned_data.get("team"),
            )

            try:
                invitation_service.send_invitation(invite, base_url=base_url)
                email_sent = True
                messages.success(
                    request,
                    _("Invitation sent to %(email)s.") % {"email": invite.email},
                )
                logger.info(
                    "InviteUserView: email sent for invitation %s → %s",
                    invite.pk,
                    invite.email,
                )
            except InvitationEmailError as exc:
                status_error = str(exc)
                messages.error(request, status_error)
                logger.error(
                    "InviteUserView: email failed for invitation %s → %s: %s",
                    invite.pk,
                    invite.email,
                    exc,
                )

            if request.htmx:
                return TemplateResponse(
                    request,
                    "companies/partials/_invite_post_success.html",
                    {
                        "pending_invitations": invitation_service.get_pending_invitations(company),
                        "invite_form": InviteUserForm(company=company),
                        "company": company,
                        "email_sent": email_sent,
                        "invite_email": invite.email if invite else "",
                        "status_error": status_error,
                    },
                )
            return redirect("companies:company_settings")

        # Form invalid
        if request.htmx:
            return TemplateResponse(
                request,
                "companies/partials/_invite_form.html",
                {"invite_form": form, "company": company},
            )
        return redirect("companies:company_settings")


class ResendInvitationView(RoleRequiredMixin, View):
    """POST /team/invite/<pk>/send/ — resend invitation email (manual retry)."""

    required_roles = [Role.MANAGER, Role.ADMIN]

    def post(self, request, pk, *args, **kwargs):
        company = get_object_or_404(Company, pk=request.user.company_id, is_active=True)
        invitation = get_object_or_404(
            Invitation,
            pk=pk,
            company=company,
            is_accepted=False,
        )

        email_sent = False
        status_error = None

        if invitation.expires_at <= timezone.now():
            status_error = str(
                _("This invitation has expired. Create a new invitation instead.")
            )
            messages.error(request, status_error)
        else:
            try:
                invitation_service.send_invitation(
                    invitation,
                    base_url=request.build_absolute_uri("/").rstrip("/"),
                )
                email_sent = True
                messages.success(
                    request,
                    _("Invitation email sent to %(email)s.") % {"email": invitation.email},
                )
            except InvitationEmailError as exc:
                status_error = str(exc)
                messages.error(request, status_error)

        if request.htmx:
            pending = invitation_service.get_pending_invitations(company)
            return TemplateResponse(
                request,
                "companies/partials/_invite_post_success.html",
                {
                    "pending_invitations": pending,
                    "invite_form": InviteUserForm(company=company),
                    "company": company,
                    "email_sent": email_sent,
                    "invite_email": invitation.email,
                    "status_error": status_error,
                },
            )
        return redirect("companies:company_settings")


class AcceptInviteView(View):
    """
    GET /invite/<token>/
    Validates the token and redirects to registration with the token pre-filled.
    Does not mark the invitation as accepted — that happens in RegisterView after signup.
    """

    def get(self, request, token, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)

        try:
            invitation = invitation_service.validate_invitation(str(token))
        except InvitationAlreadyAcceptedError:
            messages.info(request, _("This invitation has already been used."))
            return redirect("accounts:login")
        except InvitationExpiredError:
            messages.error(request, _("This invitation link has expired. Please request a new one."))
            return redirect("accounts:login")
        except InvitationNotFoundError:
            messages.error(request, _("Invalid invitation link."))
            return redirect("accounts:login")

        register_url = (
            reverse("accounts:register")
            + "?"
            + urlencode({"token": str(invitation.token)})
        )
        return redirect(register_url)
