from django.contrib import admin
from .models import Task, Comment, TaskHistory

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'team', 'assigned_to', 'status', 'priority', 'deadline')
    list_filter = ('status', 'priority', 'company')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'created_at')
    search_fields = ('body', 'task__title', 'author__email')

@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ('task', 'changed_by', 'field_name', 'created_at')
    list_filter = ('field_name', 'created_at')
    search_fields = ('task__title', 'field_name')
