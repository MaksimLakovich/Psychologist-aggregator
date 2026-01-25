from datetime import date, time, timedelta
from typing import Iterable, List, Tuple

from calendar_engine.domain.availability.user_exceptions import (
    DateAvailabilityException, TimeAvailabilityException)
from calendar_engine.models import AvailabilityException

TimeWindow = Tuple[time, time]


def _iter_days(date_from: date, date_to: date) -> Iterable[date]:
    """Вспомогательный генератор календарных дней (включительно)."""
    current = date_from
    while current <= date_to:
        yield current
        current += timedelta(days=1)


def map_exceptions_to_domain(exceptions: Iterable[AvailabilityException]) -> List:
    """Адаптирует Django-модели AvailabilityException в доменные исключения. Без этой адаптации получаем ошибку.

    Правила:
        - unavailable → DateAvailabilityException;
        - override → TimeAvailabilityException с временными окнами.

    ВАЖНО:
        - доменные исключения применяются к КОНКРЕТНОМУ дню;
        - диапазоны из БД разворачиваются в набор исключений по дням;
        - никакой бизнес-логики здесь нет - только адаптация."""

    domain_exceptions = []

    for exception in exceptions:
        for day in _iter_days(exception.exception_start, exception.exception_end):

            # Полностью закрытый день (отпуск, больничный, выходной)
            if exception.exception_type == "unavailable":
                domain_exceptions.append(
                    DateAvailabilityException(
                        day=day,
                    )
                )

            # Особый день с переопределенными окнами
            elif exception.exception_type == "override":
                time_windows: List[TimeWindow] = [
                    (window.start_time, window.end_time)
                    for window in exception.time_windows.all()
                ]

                domain_exceptions.append(
                    TimeAvailabilityException(
                        day=day,
                        time_windows=time_windows,
                    )
                )

    return domain_exceptions
