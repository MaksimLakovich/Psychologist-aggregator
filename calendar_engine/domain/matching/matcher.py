from datetime import date
from typing import List

from calendar_engine.domain.availability.dto import (AvailabilityDayDTO,
                                                     AvailabilityDTO)
from calendar_engine.domain.matching.base import AbsTimeMatcher
from calendar_engine.domain.matching.dto import MatchResultDTO


class TimeRangeMatcher(AbsTimeMatcher):
    """Выполнение временного matching по диапазону дат.
    Используется для:
        - фильтрации доступности под пользовательский запрос;
        - подготовки данных для агрегатора (поиск специалистов).
    Пример сценария:
        Пользователь выбрал диапазон дат -> matching отфильтровал слоты -> aggregator подобрал специалистов,
        у которых есть такие слоты."""

    def match(self, *, availability: AvailabilityDTO, date_from: date, date_to: date) -> MatchResultDTO:
        """Применяет временные критерии и возвращает результат matching.
        :return: Итоговая отфильтрованная доступность (DTO-объект с доступными слотами)."""
        if date_from > date_to:
            raise ValueError("date_from не может быть позже date_to")

        filtered_days: List[AvailabilityDayDTO] = []

        for day in availability.days:
            if date_from <= day.day <= date_to:
                # День может быть пустым (slots=[]), это допустимо
                filtered_days.append(day)

        filtered_availability = AvailabilityDTO(days=filtered_days)

        return MatchResultDTO(
            availability=filtered_availability,
            applied_criteria=[
                f"date_range:{date_from.isoformat()}–{date_to.isoformat()}",
            ],
        )
