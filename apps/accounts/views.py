from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import View, FormView, UpdateView, TemplateView
from django.http import HttpResponse
from django.urls import reverse

from apps.companies.services import (
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationNotFoundError,
    InvitationService,
)



from .forms import LoginForm, RegistrationForm, ProfileUpdateForm
from .mixins import RoleRequiredMixin
from .models import Role
from apps.core.mixins import HtmxTemplateResponseMixin
from apps.tasks.models import Task, TaskStatus
from apps.burnout.models import BurnoutScore
from apps.burnout.services import BurnoutService
from apps.tasks.models import Task, TaskStatus




_invitation_service = InvitationService()


class LoginView(FormView):
    form_class = LoginForm
    template_name = 'accounts/login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        success_url = self.get_success_url()
        if self.request.htmx:
            response = HttpResponse()
            response['HX-Redirect'] = success_url
            return response
        return redirect(success_url)

    def form_invalid(self, form):
        if self.request.htmx:
            return self.render_to_response(
                self.get_context_data(form=form),
                # Return only the form partial so HTMX swaps just the form
            )
        return super().form_invalid(form)

    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
            
        user = self.request.user
        if user.role in ['manager', 'admin']:
            return reverse('accounts:dashboard-manager')
        return reverse('accounts:dashboard-employee')


class LogoutView(View):
    def post(self, request, *args, **kwargs):
        logout(request)
        if request.htmx:
            response = HttpResponse()
            response['HX-Redirect'] = '/login/'
            return response
        return redirect('accounts:login')


class RegisterView(FormView):
    form_class = RegistrationForm
    template_name = 'accounts/register.html'

    def _get_token(self):
        return (
            self.request.POST.get('token')
            or self.request.GET.get('token')
            or self.kwargs.get('token')
        )

    def get_invitation(self):
        token = self._get_token()
        if not token:
            return None
        try:
            return _invitation_service.validate_invitation(str(token))
        except (
            InvitationNotFoundError,
            InvitationExpiredError,
            InvitationAlreadyAcceptedError,
        ):
            return None

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET' and request.user.is_authenticated:
            logout(request)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        invitation = self.get_invitation()
        if not invitation:
            messages.error(request, _('Invalid or expired invitation link.'))
            return redirect('accounts:login')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invitation = self.get_invitation()
        if invitation:
            context['invitation'] = invitation
        return context

    def get_initial(self):
        invitation = self.get_invitation()
        if invitation:
            return {'email': invitation.email}
        return {}

    def form_valid(self, form):
        invitation = self.get_invitation()
        if not invitation:
            messages.error(self.request, _('Invalid or expired invitation link.'))
            return redirect('accounts:login')

        user = form.save(commit=False)
        user.role = invitation.role
        user.company = invitation.company
        user.team = invitation.team
        user.save()

        _invitation_service.accept_invitation(str(invitation.token))

        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(self.request, _('Welcome to QuestFlow!'))

        if self.request.htmx:
            response = HttpResponse()
            response['HX-Redirect'] = '/'
            return response
        return redirect('/')

    def form_invalid(self, form):
        invitation = self.get_invitation()
        if not invitation:
            messages.error(self.request, _('Invalid or expired invitation link.'))
            return redirect('accounts:login')
        return self.render_to_response(
            self.get_context_data(form=form, invitation=invitation)
        )


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = ProfileUpdateForm(instance=self.request.user)
        return ctx


class ProfileUpdateView(LoginRequiredMixin, View):
    """
    HTMX-only endpoint to update the current user's profile.
    On success returns an updated profile partial; on failure returns the form partial with errors.
    """
    def post(self, request, *args, **kwargs):
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            if request.htmx:
                return self.render_success(request)
            return redirect('accounts:profile')

        if request.htmx:
            from django.template.response import TemplateResponse
            return TemplateResponse(request, 'accounts/partials/_profile_form.html', {'form': form})
        return redirect('accounts:profile')

    def render_success(self, request):
        from django.template.response import TemplateResponse
        return TemplateResponse(request, 'accounts/partials/_profile_success.html', {
            'user': request.user,
        })


class EmployeeDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/employee.html'
    required_roles = ['employee', 'manager']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        active_tasks = Task.objects.filter(
            assigned_to=user,
            company=user.company,
            status__in=['todo', 'in_progress']
        ).select_related('created_by')[:10]

        context['active_tasks'] = active_tasks
        
        return context

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     user = self.request.user

    #     # === Активные задачи для дашборда ===
    #     active_tasks = user.tasks.filter(
    #         company=user.company,
    #         status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS]
    #     ).select_related('created_by', 'assigned_to').order_by('deadline', 'priority')[:8]

    #     context['active_tasks'] = active_tasks

    #     # Дополнительно можно добавить другие полезные данные
    #     context['total_active_tasks'] = active_tasks.count()

    #     return context



class ManagerDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/manager.html'
    required_roles = ['manager', 'admin']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if hasattr(self.request.user, 'team') and self.request.user.team:
            team = self.request.user.team
            ctx['burnout_stats'] = BurnoutService.get_team_summary(team)
            
            # Team members with prefetched relations
            ctx['team_members'] = team.user_set.select_related(
                'level_data', 'streak', 'burnout_score'
            ).exclude(id=self.request.user.id).order_by('first_name', 'last_name')
            
            # Team Kanban Tasks
            tasks = Task.objects.filter(
                assigned_to__team=team, 
                is_deleted=False
            ).select_related('assigned_to', 'created_by')
            
            kanban_columns = {
                TaskStatus.TODO: [t for t in tasks if t.status == TaskStatus.TODO],
                TaskStatus.IN_PROGRESS: [t for t in tasks if t.status == TaskStatus.IN_PROGRESS],
                TaskStatus.DONE: [t for t in tasks if t.status == TaskStatus.DONE],
                TaskStatus.OVERDUE: [t for t in tasks if t.status == TaskStatus.OVERDUE],
            }
            ctx['kanban_columns'] = kanban_columns
            ctx['TaskStatus'] = TaskStatus
        else:
            ctx['burnout_stats'] = {'green': 0, 'yellow': 0, 'red': 0, 'total': 0}
            ctx['team_members'] = []
            ctx['kanban_columns'] = {}
        return ctx


class BurnoutBadgePartialView(LoginRequiredMixin, HtmxTemplateResponseMixin, TemplateView):
    template_name = 'dashboard/partials/_burnout_badge.html'
    htmx_template_name = 'dashboard/partials/_burnout_badge.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            score = self.request.user.burnout_score
            ctx['burnout_score'] = score
            ctx['burnout_status'] = score.score
            
            labels = {'green': 'Healthy', 'yellow': 'At Risk', 'red': 'Burned Out'}
            ctx['burnout_label'] = labels.get(score.score, 'Unknown')
        except BurnoutScore.DoesNotExist:
            ctx['burnout_score'] = None
            ctx['burnout_status'] = 'none'
            ctx['burnout_label'] = 'Not Assessed'
            
        return ctx

class BurnoutConsentToggleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        service = BurnoutService(request.user)
        try:
            current_score = request.user.burnout_score
            new_consent = not current_score.manager_consent
        except BurnoutScore.DoesNotExist:
            new_consent = True
            
        service.set_manager_consent(new_consent)
        
        # We can just redirect back to the badge partial view
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse('accounts:dashboard-burnout-badge'))
