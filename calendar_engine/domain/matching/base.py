from abc import ABC, abstractmethod
from datetime import date

from calendar_engine.domain.availability.dto import AvailabilityDTO
from calendar_engine.domain.matching.dto import MatchResultDTO


class AbsTimeMatcher(ABC):
    """Абстрактный контракт временного matching.
    Задача matching:
        - принять доступность специалиста;
        - применить временные критерии (даты, слоты, ограничения);
        - вернуть отфильтрованную доступность.
    ВАЖНО:
        - matching НЕ знает ничего про специалистов;
        - matching НЕ знает ничего про UI, HTTP, БД;
        - matching работает ТОЛЬКО с доменными DTO."""

    @abstractmethod
    def match(self, *, availability: AvailabilityDTO, date_from: date, date_to: date) -> MatchResultDTO:
        """Применяет временные критерии и возвращает результат matching.
        :return: Итоговая отфильтрованная доступность (AvailabilityDTO - DTO-объект с доступными слотами)."""
        raise NotImplementedError
