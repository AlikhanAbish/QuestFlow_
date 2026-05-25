from django import forms
from apps.burnout.models import AssessmentForm

class SelfAssessmentForm(forms.ModelForm):
    class Meta:
        model = AssessmentForm
        fields = ['ex1', 'ex2', 'ex3', 'cy1', 'cy2', 'cy3', 'ef1', 'ef2', 'ef3']
        widgets = {
            'ex1': forms.RadioSelect(choices=[(i, str(i)) for i in range(7)]),
            'ex2': forms.RadioSelect(choices=[(i, str(i)) for i in range(7)]),
            'ex3': forms.RadioSelect(choices=[(i, str(i)) for i in range(7)]),
            'cy1': forms.RadioSelect(choices=[(i, str(i)) for i in range(7)]),
            'cy2': forms.RadioSelect(choices=[(i, str(i)) for i in range(7)]),
            'cy3': forms.RadioSelect(choices=[(i, str(i)) for i in range(7)]),
            'ef1': forms.RadioSelect(choices=[(i, str(i)) for i in range(7)]),
            'ef2': forms.RadioSelect(choices=[(i, str(i)) for i in range(7)]),
            'ef3': forms.RadioSelect(choices=[(i, str(i)) for i in range(7)]),
        }
