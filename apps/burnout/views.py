from django.views import View
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from apps.accounts.mixins import RoleRequiredMixin
from apps.burnout.forms import SelfAssessmentForm
from apps.burnout.services import BurnoutService
from apps.burnout.models import AssessmentForm, BurnoutScore

class BurnoutAssessmentView(RoleRequiredMixin, View):
    required_roles = ['employee', 'manager', 'admin']
    
    def get(self, request):
        now = timezone.now()
        
        # Check if already submitted this week
        iso_year, iso_week, _ = now.isocalendar()
        already_submitted = AssessmentForm.objects.filter(
            user=request.user, 
            year=iso_year, 
            week_number=iso_week
        ).exists()

        form = SelfAssessmentForm()
        context = {
            'form': form,
            'already_submitted': already_submitted,
        }
        
        # If HTMX request and we just want the form
        if request.htmx:
            return render(request, 'partials/_burnout_form.html', context)
            
        return render(request, 'burnout/assessment.html', context)

class BurnoutAssessmentSubmitView(RoleRequiredMixin, View):
    required_roles = ['employee', 'manager', 'admin']
    
    def post(self, request):
        if not request.htmx:
            return HttpResponseForbidden("Direct access not allowed")
        
        now = timezone.now()
        iso_year, iso_week, _ = now.isocalendar()
        
        # Check if already submitted this week
        already_submitted = AssessmentForm.objects.filter(
            user=request.user,
            year=iso_year,
            week_number=iso_week
        ).exists()
        
        if already_submitted:
            return render(request, 'partials/_burnout_message.html', {
                'message': 'Вы уже прошли self-assessment на этой неделе. Попробуйте снова в следующий понедельник.',
                'type': 'info'
            })
            
        form = SelfAssessmentForm(request.POST)
        if form.is_valid():
            service = BurnoutService(request.user)
            score = service.process_assessment(form.cleaned_data)
            return render(request, 'partials/_burnout_result.html', {'score': score})
            
        # Form invalid
        return render(request, 'partials/_burnout_form.html', {
            'form': form,
            'already_submitted': False
        })

class BurnoutHistoryView(RoleRequiredMixin, View):
    required_roles = ['employee', 'manager', 'admin']
    
    def get(self, request):
        assessments = AssessmentForm.objects.filter(user=request.user).order_by('-year', '-week_number')
        score = BurnoutScore.objects.filter(user=request.user).first()
        
        context = {
            'assessments': assessments,
            'current_score': score,
        }
        
        if request.htmx:
            return render(request, 'partials/_burnout_history.html', context)
        return render(request, 'burnout/history.html', context)

class TeamBurnoutSummaryView(RoleRequiredMixin, View):
    required_roles = ['manager', 'admin']
    
    def get(self, request):
        team = request.user.team
        if not team:
            return HttpResponseForbidden("You are not assigned to a team.")
            
        summary = BurnoutService.get_team_summary(team)
        
        context = {
            'team': team,
            'summary': summary
        }
        
        if request.htmx:
            return render(request, 'partials/_team_burnout_summary.html', context)
        return render(request, 'burnout/team_summary.html', context)
