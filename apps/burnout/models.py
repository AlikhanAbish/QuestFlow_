from django.db import models
from django.core.validators import MaxValueValidator
from django.conf import settings
from apps.core.models import TimeStampedModel

class BurnoutLevel(models.TextChoices):
    GREEN  = 'green',  'Healthy'
    YELLOW = 'yellow', 'At Risk'
    RED    = 'red',    'Burned Out'

class AssessmentForm(TimeStampedModel):
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assessments')
    week_number  = models.PositiveIntegerField()  # ISO week
    year         = models.PositiveIntegerField()
    # Exhaustion subscale (0-6 each)
    ex1 = models.PositiveSmallIntegerField(validators=[MaxValueValidator(6)])
    ex2 = models.PositiveSmallIntegerField(validators=[MaxValueValidator(6)])
    ex3 = models.PositiveSmallIntegerField(validators=[MaxValueValidator(6)])
    # Cynicism subscale
    cy1 = models.PositiveSmallIntegerField(validators=[MaxValueValidator(6)])
    cy2 = models.PositiveSmallIntegerField(validators=[MaxValueValidator(6)])
    cy3 = models.PositiveSmallIntegerField(validators=[MaxValueValidator(6)])
    # Professional Efficacy subscale (reversed scoring)
    ef1 = models.PositiveSmallIntegerField(validators=[MaxValueValidator(6)])
    ef2 = models.PositiveSmallIntegerField(validators=[MaxValueValidator(6)])
    ef3 = models.PositiveSmallIntegerField(validators=[MaxValueValidator(6)])
    tasks_completion_rate = models.FloatField()  # % задач в срок за неделю

    class Meta:
        unique_together = [['user', 'week_number', 'year']]

class BurnoutScore(TimeStampedModel):
    user         = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='burnout_score')
    score        = models.CharField(max_length=10, choices=BurnoutLevel.choices, default=BurnoutLevel.GREEN)
    last_calculated = models.DateTimeField(auto_now=True)
    exhaustion_avg  = models.FloatField(default=0)
    cynicism_avg    = models.FloatField(default=0)
    efficacy_avg    = models.FloatField(default=0)
    manager_consent = models.BooleanField(default=False)
