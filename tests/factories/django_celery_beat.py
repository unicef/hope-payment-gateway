from django.utils import timezone

from django_celery_beat.models import SOLAR_SCHEDULES, ClockedSchedule, IntervalSchedule, SolarSchedule
from factory.fuzzy import FuzzyChoice

from .base import AutoRegisterModelFactory


class IntervalScheduleFactory(AutoRegisterModelFactory):
    every = 1
    period = IntervalSchedule.HOURS

    class Meta:
        model = IntervalSchedule


class SolarScheduleFactory(AutoRegisterModelFactory):
    event = FuzzyChoice([x[0] for x in SOLAR_SCHEDULES])

    latitude = 10.1
    longitude = 10.1

    class Meta:
        model = SolarSchedule


class ClockedScheduleFactory(AutoRegisterModelFactory):
    clocked_time = timezone.now()

    class Meta:
        model = ClockedSchedule
