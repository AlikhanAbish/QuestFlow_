from django.urls import path

from . import views

app_name = "companies"

urlpatterns = [
    # Company settings
    path("company/settings/", views.CompanySettingsView.as_view(), name="company_settings"),
    path("company/create/", views.CompanyCreateView.as_view(), name="company_create"),
    path("company/teams/create/", views.TeamCreateView.as_view(), name="team_create"),
    path("company/settings/update/", views.CompanyUpdateView.as_view(), name="company_update"),

    # Team members
    path("team/members/", views.TeamMembersView.as_view(), name="team_members"),
    path("team/invite/", views.InviteUserView.as_view(), name="team_invite"),
    path(
        "team/invite/<int:pk>/send/",
        views.ResendInvitationView.as_view(),
        name="invitation_send",
    ),
    path("team/members/<int:pk>/role/", views.UpdateMemberRoleView.as_view(), name="member_role"),
    path("team/members/<int:pk>/remove/", views.RemoveMemberView.as_view(), name="member_remove"),

    # Invitation accept (token is a UUID)
    path("invite/<uuid:token>/", views.AcceptInviteView.as_view(), name="accept_invite"),
]
