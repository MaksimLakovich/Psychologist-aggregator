from typing import List

from calendar_engine.application.use_cases.base import AbsUseCase
from calendar_engine.domain.availability.domain_slot_generator import \
    DomainSlotGenerator
from calendar_engine.domain.availability.dto import SlotDTO
from calendar_engine.domain.availability.get_user_slots import \
    AvailabilitySlotFilter


class GenerateSpecialistScheduleUseCase(AbsUseCase):
    """Use-case получения актуального расписания специалиста (в TZ СПЕЦИАЛИСТА).
    Ответственность:
        - сгенерировать доменные слоты;
        - отфильтровать их по AvailabilityRule / AvailabilityException / Booking;
        - вернуть список доступных SlotDTO."""

    def __init__(
        self, *, slot_generator: DomainSlotGenerator, slot_filter: AvailabilitySlotFilter, date_from, days_ahead: int
    ) -> None:
        """
        :param slot_generator: Генерирует все возможные доменные временные слоты по правилам домена.
        :param slot_filter: Фильтр всех возможных доменных слотов по индивидуальным правилам доступности специалиста.
        :param date_from: Текущая дата в timezone специалиста.
        :param days_ahead: Количество дней на которое рассчитывается расписание специалиста.
        """
        self._slot_generator = slot_generator
        self._slot_filter = slot_filter
        self._date_from = date_from
        self._days_ahead = days_ahead

    def execute(self) -> List[SlotDTO]:
        """Генерируем все возможные доменные временные слоты и выполняем бизнес-операцию
        получения расписания специалиста с учетом рабочего расписания и действующих исключений в нем.

        :return: Список доступных слотов специалиста (расписание специалиста)."""

        domain_slots = self._slot_generator.generate_domain_slots(
            date_from=self._date_from,
            days_ahead=self._days_ahead,
        )

        return self._slot_filter.filter_user_slots(
            domain_slots=domain_slots
        )
