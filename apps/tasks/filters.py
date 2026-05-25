import django_filters
from django.forms.widgets import TextInput, Select
from .models import Task

class TaskFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(
        lookup_expr='icontains', 
        widget=TextInput(attrs={'placeholder': 'Search by title...'})
    )
    
    class Meta:
        model = Task
        fields = ['assigned_to', 'status', 'priority', 'team']

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if self.company:
            self.filters['assigned_to'].queryset = self.filters['assigned_to'].queryset.filter(company=self.company)
            self.filters['team'].queryset = self.filters['team'].queryset.filter(company=self.company)
