from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Task, Comment, TaskStatus

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'priority', 'deadline', 'team']
        widgets = {
            'title': forms.TextInput(attrs={
                'type': 'text',
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': _('Task title'),
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': _('Task description'),
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-indigo-500 focus:border-indigo-500',
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-indigo-500 focus:border-indigo-500',
            }),
            'deadline': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-indigo-500 focus:border-indigo-500',
            }),
            'team': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-indigo-500 focus:border-indigo-500',
            }),
        }
        
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if self.company:
            # Limit assigned_to to users in the same company
            self.fields['assigned_to'].queryset = self.fields['assigned_to'].queryset.filter(company=self.company)
            # Limit team to teams in the same company
            self.fields['team'].queryset = self.fields['team'].queryset.filter(company=self.company)


class TaskStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['status']


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 3, 'placeholder': _('Write a comment...')}),
        }
