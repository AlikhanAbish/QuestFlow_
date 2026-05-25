from django.views.generic import TemplateView, ListView, CreateView, DetailView, View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy
from apps.accounts.mixins import RoleRequiredMixin
from apps.core.mixins import HtmxTemplateResponseMixin
from apps.companies.models import Company
from apps.accounts.models import User
from apps.gamification.models import GamificationRule, Badge
from .models import AuditLog, SystemSetting
from django.db.models import Count

class BaseAdminView(RoleRequiredMixin):
    required_roles = ['admin']

class AdminDashboardView(BaseAdminView, TemplateView):
    template_name = 'admin_panel/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_companies'] = Company.objects.count()
        context['active_companies'] = Company.objects.filter(is_active=True).count()
        context['total_users'] = User.objects.count()
        context['recent_logs'] = AuditLog.objects.select_related('user').order_by('-created_at')[:5]
        return context

class AdminCompanyListView(BaseAdminView, HtmxTemplateResponseMixin, ListView):
    model = Company
    template_name = 'admin_panel/companies/list.html'
    htmx_template_name = 'admin_panel/companies/_list_partial.html'
    context_object_name = 'companies'
    paginate_by = 20
    
    def get_queryset(self):
        qs = super().get_queryset().annotate(user_count=Count('user'))
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

class AdminCompanyCreateView(BaseAdminView, CreateView):
    model = Company
    fields = ['name', 'slug', 'owner', 'max_users']
    template_name = 'admin_panel/companies/create.html'
    success_url = reverse_lazy('admin_panel:company-list')

class AdminCompanyDetailView(BaseAdminView, DetailView):
    model = Company
    template_name = 'admin_panel/companies/detail.html'
    context_object_name = 'company'

class AdminCompanyDeactivateView(BaseAdminView, View):
    def post(self, request, pk):
        company = get_object_or_404(Company, pk=pk)
        company.is_active = not company.is_active
        company.save()
        AuditLog.objects.create(
            user=request.user,
            action=f"{'Activated' if company.is_active else 'Deactivated'} company {company.name}"
        )
        return render(request, 'admin_panel/companies/_status_partial.html', {'company': company})

class AdminUserListView(BaseAdminView, HtmxTemplateResponseMixin, ListView):
    model = User
    template_name = 'admin_panel/users/list.html'
    htmx_template_name = 'admin_panel/users/_list_partial.html'
    context_object_name = 'users'
    paginate_by = 50
    
    def get_queryset(self):
        qs = super().get_queryset().select_related('company')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(email__icontains=q)
        return qs

class AdminUserRoleView(BaseAdminView, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        role = request.POST.get('role')
        if role in ['employee', 'manager', 'admin']:
            user.role = role
            user.save()
            AuditLog.objects.create(
                user=request.user,
                action=f"Changed role of {user.email} to {role}"
            )
        return render(request, 'admin_panel/users/_row_partial.html', {'user': user})

class AdminUserDeactivateView(BaseAdminView, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_active = not user.is_active
        user.save()
        AuditLog.objects.create(
            user=request.user,
            action=f"{'Activated' if user.is_active else 'Deactivated'} user {user.email}"
        )
        return render(request, 'admin_panel/users/_row_partial.html', {'user': user})

class AdminGamificationSettingsView(BaseAdminView, ListView):
    model = GamificationRule
    template_name = 'admin_panel/gamification/settings.html'
    context_object_name = 'rules'

class AdminGamificationRulesUpdateView(BaseAdminView, View):
    def post(self, request):
        for key, value in request.POST.items():
            if key.startswith('rule_'):
                rule_id = key.split('_')[1]
                GamificationRule.objects.filter(pk=rule_id).update(points=value)
        AuditLog.objects.create(
            user=request.user,
            action="Updated gamification rules"
        )
        return redirect('admin_panel:gamification-settings')

class AdminBadgeListView(BaseAdminView, ListView):
    model = Badge
    template_name = 'admin_panel/gamification/badges.html'
    context_object_name = 'badges'

class AdminBadgeCreateView(BaseAdminView, CreateView):
    model = Badge
    fields = ['name', 'description', 'icon', 'trigger_type', 'trigger_value']
    template_name = 'admin_panel/gamification/badge_form.html'
    success_url = reverse_lazy('admin_panel:gamification-badges')

class AdminAuditLogView(BaseAdminView, HtmxTemplateResponseMixin, ListView):
    model = AuditLog
    template_name = 'admin_panel/audit_log.html'
    htmx_template_name = 'admin_panel/_audit_log_partial.html'
    context_object_name = 'logs'
    paginate_by = 50

class AdminSystemSettingsView(BaseAdminView, ListView):
    model = SystemSetting
    template_name = 'admin_panel/settings.html'
    context_object_name = 'settings'
