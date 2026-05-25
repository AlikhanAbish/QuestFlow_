from statistics import mean
from apps.burnout.models import AssessmentForm, BurnoutLevel

class MBICalculator:
    EXHAUSTION_THRESHOLD  = {'yellow': 2.0, 'red': 4.0}
    CYNICISM_THRESHOLD    = {'yellow': 1.5, 'red': 3.0}
    EFFICACY_THRESHOLD    = {'yellow': 3.5, 'red': 2.0}  # Reversed: low = bad
    COMPLETION_THRESHOLD  = {'yellow': 0.7, 'red': 0.5}

    def calculate(self, form: AssessmentForm) -> BurnoutLevel:
        ex_avg = mean([form.ex1, form.ex2, form.ex3])
        cy_avg = mean([form.cy1, form.cy2, form.cy3])
        ef_avg = mean([form.ef1, form.ef2, form.ef3])
        completion = form.tasks_completion_rate

        red_flags = sum([
            ex_avg >= self.EXHAUSTION_THRESHOLD['red'],
            cy_avg >= self.CYNICISM_THRESHOLD['red'],
            ef_avg <= self.EFFICACY_THRESHOLD['red'],
            completion < self.COMPLETION_THRESHOLD['red'],
        ])
        if red_flags >= 2: return BurnoutLevel.RED

        yellow_flags = sum([
            ex_avg >= self.EXHAUSTION_THRESHOLD['yellow'],
            cy_avg >= self.CYNICISM_THRESHOLD['yellow'],
            ef_avg <= self.EFFICACY_THRESHOLD['yellow'],
            completion < self.COMPLETION_THRESHOLD['yellow'],
        ])
        if yellow_flags >= 2: return BurnoutLevel.YELLOW

        return BurnoutLevel.GREEN
