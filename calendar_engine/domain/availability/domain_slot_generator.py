from datetime import date, timedelta
from typing import List

from calendar_engine.constants import DOMAIN_TIME_POLICY
from calendar_engine.domain.availability.dto import SlotDTO


class DomainSlotGenerator:
    """Генерирует все возможные доменные временные слоты по правилам домена."""

    def generate_domain_slots(self, *, date_from: date, days_ahead: int) -> List[SlotDTO]:
        """Выполняет генерацию всех возможных доменных временных слотов.

        :param date_from: Дата с которой начинается генерация доменных временных слотов.
        :param days_ahead: На какое количество дней вперед выполняется генерация слотов.
        :return: Список SlotDTO.
        """

        domain_slots: List[SlotDTO] = []

        # Генерируем доменные слоты для КАЛЕНДАРНОГО ДНЯ клиента.
        # Запускаем цикл по последовательности чисел (DAYS_AHEAD: 7 дней): 0, 1, 2, 3, 4, 5, 6
        for day_offset in range(days_ahead):
            day = date_from + timedelta(days=day_offset)

            for start, end in DOMAIN_TIME_POLICY.iter_domain_day_slots(day):
                domain_slots.append(
                    SlotDTO(
                        day=day,
                        start=start,
                        end=end,
                    )
                )

        return domain_slots
