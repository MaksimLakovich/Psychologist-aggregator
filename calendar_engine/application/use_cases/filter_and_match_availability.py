from typing import Iterable

from calendar_engine.application.use_cases.base import AbsUseCase
from calendar_engine.domain.availability.dto import SlotDTO
from calendar_engine.domain.availability.get_user_slots import \
    AvailabilitySlotFilter
from calendar_engine.domain.matching.base import AbsSlotMatcher
from calendar_engine.domain.matching.dto import MatchResultDTO


class FilterAndMatchSlotsUseCase(AbsUseCase):
    """Use-case фильтрации и matching предпочитаемых клиентом слотов с доступными слотами специалиста.

    Прикладной сценарий:
        1) принять все возможные доменные слоты (сгенерированные по правилам домена);
        2) отфильтровать их по индивидуальным правилам доступности специалиста (рабочие окна);
        3) применить matching-логику (учесть предпочитаемые пользователем доменные слоты);
        4) вернуть результат matching (пересечение - минимум одно совпадение).

    ВАЖНО:
        - use-case НЕ генерирует доменные слоты;
        - use-case НЕ знает про БД, HTTP, пользователей;
        - критерии matching полностью инкапсулированы в matcher-е."""

    def __init__(self, *, slot_filter: AvailabilitySlotFilter, matcher: AbsSlotMatcher) -> None:
        """
        :param slot_filter: Фильтр всех возможных доменных слотов по индивидуальным правилам доступности специалиста.
        :param matcher: Domain-matcher, применяющий пользовательские критерии.
        """
        self._slot_filter = slot_filter
        self._matcher = matcher

    def execute(self, *, domain_slots: Iterable[SlotDTO]) -> MatchResultDTO:
        """Запускает сценарий фильтрации и matching слотов.

        :param domain_slots: Все возможные доменные временные слоты (результат DomainSlotGenerator).
        :return: MatchResultDTO - результат domain-matching."""

        # 1) Фильтруем доменные слоты по доступности специалиста (по рабочему расписанию)
        allowed_slots = self._slot_filter.filter_user_slots(
            domain_slots=domain_slots
        )

        # 2) Применяем matching
        return self._matcher.match(
            allowed_slots=allowed_slots
        )
