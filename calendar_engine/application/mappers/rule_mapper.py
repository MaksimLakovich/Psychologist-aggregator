from typing import List, Tuple
from datetime import time

from calendar_engine.domain.availability.user_rules import WeeklyAvailabilityRule
from calendar_engine.models import AvailabilityRule


TimeWindow = Tuple[time, time]


def map_rule_to_domain(rule: AvailabilityRule) -> WeeklyAvailabilityRule:
    """Адаптирует Django-модель AvailabilityRule в доменное правило WeeklyAvailabilityRule.
    Без этой адаптации получаем ошибку.

    Что делает:
        - берет рабочие дни недели;
        - собирает все временные окна внутри дня;
        - возвращает доменный объект без бизнес-логики."""

    time_windows: List[TimeWindow] = [
        (window.start_time, window.end_time)
        for window in rule.time_windows.all()
    ]

    return WeeklyAvailabilityRule(
        weekdays=set(rule.weekdays),
        time_windows=time_windows,
    )
