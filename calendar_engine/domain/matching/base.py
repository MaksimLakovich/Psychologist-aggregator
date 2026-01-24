from abc import ABC, abstractmethod
from typing import Iterable

from calendar_engine.domain.availability.dto import SlotDTO
from calendar_engine.domain.matching.dto import MatchResultDTO


class AbsSlotMatcher(ABC):
    """Абстрактный контракт domain-matching по временным слотам.

    Ответственность matcher-а:
        - принять доступные слоты специалиста;
        - принять предпочитаемые клиентом слоты;
        - вернуть пересечение слотов.
    ВАЖНО:
        - matcher не знает про БД, пользователей, UI;
        - matcher работает ТОЛЬКО с SlotDTO;
        - matcher НЕ группирует слоты по дням."""

    @abstractmethod
    def match(self, *, allowed_slots: Iterable[SlotDTO]) -> MatchResultDTO:
        """Выполняет matching и возвращает результат.

        :param allowed_slots: Доменные слоты специалиста, которые были отфильтрованы по его
        индивидуальным правилам доступности. То есть, по рабочему расписанию с учетом исключений;
        :return: DTO-объект со списком SlotDTO, которые совпали с предпочитаемыми клиентом слотами."""
        raise NotImplementedError
