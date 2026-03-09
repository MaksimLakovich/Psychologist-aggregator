from datetime import datetime, timedelta
from typing import Dict, List

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
        self,
        *,
        slot_generator: DomainSlotGenerator,
        slot_filter: AvailabilitySlotFilter,
        date_from,
        days_ahead: int,
        current_datetime,
        minimum_booking_notice_hours: int,
        override_minimum_booking_notice_hours_by_day: Dict,
    ) -> None:
        """
        :param slot_generator: Генерирует все возможные доменные временные слоты по правилам домена.
        :param slot_filter: Фильтр всех возможных доменных слотов по индивидуальным правилам доступности специалиста.
        :param date_from: Текущая дата в timezone специалиста.
        :param days_ahead: Количество дней на которое рассчитывается расписание специалиста.
        :param current_datetime: Текущее время в timezone специалиста.
        :param minimum_booking_notice_hours: Базовое минимальное количество часов до старта слота для записи.
        :param override_minimum_booking_notice_hours_by_day:
            Словарь вида {date: hours}, который позволяет на отдельные даты переопределить базовый minimum notice.
        """
        self._slot_generator = slot_generator
        self._slot_filter = slot_filter
        self._date_from = date_from
        self._days_ahead = days_ahead
        self._current_datetime = current_datetime
        self._minimum_booking_notice_hours = minimum_booking_notice_hours
        self._override_minimum_booking_notice_hours_by_day = override_minimum_booking_notice_hours_by_day

    def execute(self) -> List[SlotDTO]:
        """Генерируем все возможные доменные временные слоты и выполняем бизнес-операцию
        получения расписания специалиста с учетом рабочего расписания и действующих исключений в нем.

        :return: Список доступных слотов специалиста (расписание специалиста)."""

        domain_slots = self._slot_generator.generate_domain_slots(
            date_from=self._date_from,
            days_ahead=self._days_ahead,
        )

        allowed_slots = self._slot_filter.filter_user_slots(
            domain_slots=domain_slots
        )

        # После того как получили все допустимые слоты специалиста по рабочему расписанию и исключениям,
        # дополнительно отсекаем слишком "близкие" к текущему моменту слоты.
        # Бизнес-смысл:
        #   - если сейчас 10:57, а minimum_booking_notice_hours = 1 час,
        #   - то слот на 11:00 не должен показываться клиенту как доступный для записи.
        filtered_by_notice: List[SlotDTO] = []

        for slot in allowed_slots:
            effective_minimum_booking_notice_hours = self._override_minimum_booking_notice_hours_by_day.get(
                slot.day,
                self._minimum_booking_notice_hours,
            )

            earliest_allowed_start = self._current_datetime + timedelta(
                hours=effective_minimum_booking_notice_hours
            )

            slot_start_datetime = datetime.combine(
                slot.day,
                slot.start,
                tzinfo=self._current_datetime.tzinfo,
            )

            if slot_start_datetime >= earliest_allowed_start:
                filtered_by_notice.append(slot)

        return filtered_by_notice
