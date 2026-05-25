from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.views.generic.detail import SingleObjectMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import messages
import csv

from .models import Task, Comment, TaskStatus, Priority
from .services import TaskService
from .forms import TaskForm
from apps.core.mixins import HtmxTemplateResponseMixin, CompanyIsolationMixin
from apps.accounts.mixins import RoleRequiredMixin
from .filters import TaskFilter

from django.db.models import Q

class BaseTaskMixin(LoginRequiredMixin, CompanyIsolationMixin):
    model = Task
    
    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.select_related('assigned_to', 'created_by', 'team')
        
        # Role-based filtering
        user = self.request.user
        
        if user.role == 'employee':
            # Employees see only tasks assigned to them
            qs = qs.filter(assigned_to=user)
        elif user.role == 'manager':
            # Managers see:
            # 1. Tasks assigned to team members of teams they manage
            # 2. Tasks they created
            qs = qs.filter(
                Q(assigned_to__team__manager=user) |  # Tasks for their team members
                Q(created_by=user)                     # Tasks they created
            )
        # Admin (role == 'admin') sees all tasks in the company (no additional filtering)
        
        return qs.distinct()

class TaskListView(BaseTaskMixin, HtmxTemplateResponseMixin, ListView):
    template_name = 'tasks/task_list.html'
    htmx_template_name = 'partials/_task_list.html'
    context_object_name = 'tasks'

    def get_queryset(self):
        qs = super().get_queryset()
        self.filterset = TaskFilter(self.request.GET, queryset=qs, company=self.request.user.company)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = getattr(self, 'filterset', None)
        return context

class TaskFilterPartialView(TaskListView):
    # Same as TaskListView, but forced to return partial because we map it to HTMX explicit endpoint if we want
    template_name = 'partials/_task_list.html'
    
    def get_template_names(self):
        return [self.template_name]

class TaskKanbanView(BaseTaskMixin, HtmxTemplateResponseMixin, ListView):
    template_name = 'tasks/task_kanban.html'
    htmx_template_name = 'partials/_task_kanban.html'
    context_object_name = 'tasks'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tasks = context['tasks']
        
        kanban_columns = {
            TaskStatus.TODO: [t for t in tasks if t.status == TaskStatus.TODO],
            TaskStatus.IN_PROGRESS: [t for t in tasks if t.status == TaskStatus.IN_PROGRESS],
            TaskStatus.DONE: [t for t in tasks if t.status == TaskStatus.DONE],
            TaskStatus.OVERDUE: [t for t in tasks if t.status == TaskStatus.OVERDUE],
        }
        
        context['kanban_columns'] = kanban_columns
        context['TaskStatus'] = TaskStatus
        return context

class TaskCreateView(RoleRequiredMixin, BaseTaskMixin, HtmxTemplateResponseMixin, CreateView):
    required_roles = ['manager', 'admin']
    form_class = TaskForm
    template_name = 'tasks/task_form.html'
    htmx_template_name = 'partials/_task_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs
    
    def form_valid(self, form):
        kwargs = form.cleaned_data
        task = TaskService.create_task(
            company=self.request.user.company,
            created_by=self.request.user,
            **kwargs
        )
        messages.success(self.request, 'Task created successfully.')
        if getattr(self.request, 'htmx', False):
            response = HttpResponse()
            response['HX-Trigger'] = 'taskCreated'
            # Use HX-Redirect to reload page
            response['HX-Redirect'] = reverse('tasks:task_list')
            return response
        return redirect('tasks:task_list')
    
    def form_invalid(self, form):
        if getattr(self.request, 'htmx', False):
            return self.render_to_response(self.get_context_data(form=form))
        return super().form_invalid(form)

class TaskDetailView(BaseTaskMixin, HtmxTemplateResponseMixin, DetailView):
    template_name = 'tasks/task_detail.html'
    htmx_template_name = 'partials/_task_detail.html'
    context_object_name = 'task'

class TaskUpdateView(RoleRequiredMixin, BaseTaskMixin, HtmxTemplateResponseMixin, UpdateView):
    required_roles = ['manager', 'admin']
    form_class = TaskForm
    template_name = 'tasks/task_form.html'
    htmx_template_name = 'partials/_task_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs
    
    def form_valid(self, form):
        task = self.get_object()
        TaskService.update_task(
            task=task,
            changed_by=self.request.user,
            **form.cleaned_data
        )
        messages.success(self.request, 'Task updated successfully.')
        if getattr(self.request, 'htmx', False):
            response = HttpResponse()
            response['HX-Trigger'] = 'taskUpdated'
            return response
        return redirect('tasks:task_detail', pk=task.pk)

class TaskDeleteView(RoleRequiredMixin, BaseTaskMixin, DeleteView):
    required_roles = ['manager', 'admin']
    success_url = reverse_lazy('tasks:task_list')
    
    def delete(self, request, *args, **kwargs):
        task = self.get_object()
        task.delete() # SoftDeleteModel handles this
        if getattr(request, 'htmx', False):
            response = HttpResponse()
            response['HX-Trigger'] = 'taskDeleted'
            return response
        return super().delete(request, *args, **kwargs)

class TaskStatusUpdateView(LoginRequiredMixin, View):
    """HTMX endpoint to update task status."""
    def post(self, request, pk, *args, **kwargs):
        user = request.user
        task = get_object_or_404(Task, pk=pk, company=user.company)
        
        # Role-based access control
        if user.role == 'employee' and task.assigned_to != user:
            return HttpResponseForbidden('You can only update tasks assigned to you.')
        elif user.role == 'manager':
            # Manager can update if task is assigned to their team member or they created it
            is_team_task = task.assigned_to and task.assigned_to.team and task.assigned_to.team.manager == user
            is_own_task = task.created_by == user
            if not (is_team_task or is_own_task):
                return HttpResponseForbidden('You can only update tasks in your team.')
        
        new_status = request.POST.get('status')
        if new_status in [choice[0] for choice in TaskStatus.choices]:
            TaskService.change_task_status(task, request.user, new_status)
        
        response = HttpResponse()
        response['HX-Trigger'] = 'taskStatusUpdated'
        return response

class TaskCommentView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        user = request.user
        task = get_object_or_404(Task, pk=pk, company=user.company)
        
        # Role-based access control
        if user.role == 'employee' and task.assigned_to != user:
            return HttpResponseForbidden('You can only comment on tasks assigned to you.')
        elif user.role == 'manager':
            is_team_task = task.assigned_to and task.assigned_to.team and task.assigned_to.team.manager == user
            is_own_task = task.created_by == user
            if not (is_team_task or is_own_task):
                return HttpResponseForbidden('You can only comment on tasks in your team.')
        
        body = request.POST.get('body')
        if body:
            TaskService.add_comment(task, request.user, body)
            
        if getattr(request, 'htmx', False):
            response = HttpResponse()
            response['HX-Trigger'] = 'commentAdded'
            return response
        return redirect('tasks:task_detail', pk=pk)

class TaskCommentsPartialView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        user = request.user
        task = get_object_or_404(Task, pk=pk, company=user.company)
        
        # Role-based access control
        if user.role == 'employee' and task.assigned_to != user:
            return HttpResponseForbidden('You can only view comments on tasks assigned to you.')
        elif user.role == 'manager':
            is_team_task = task.assigned_to and task.assigned_to.team and task.assigned_to.team.manager == user
            is_own_task = task.created_by == user
            if not (is_team_task or is_own_task):
                return HttpResponseForbidden('You can only view comments on tasks in your team.')
        
        comments = task.comments.select_related('author').all()
        from django.shortcuts import render
        return render(request, 'partials/_comments_list.html', {'comments': comments, 'task': task})

class TaskExportCSVView(RoleRequiredMixin, BaseTaskMixin, View):
    required_roles = ['manager', 'admin']
    
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tasks.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Title', 'Status', 'Priority', 'Assigned To', 'Created By', 'Created At'])
        
        for task in self.get_queryset():
            writer.writerow([
                task.pk,
                task.title,
                task.get_status_display(),
                task.get_priority_display(),
                task.assigned_to.email if task.assigned_to else '',
                task.created_by.email if task.created_by else '',
                task.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
            
        return response
