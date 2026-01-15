from datetime import datetime, timedelta

from django.utils.timezone import make_aware, now

from calendar_engine.application.use_cases.base import AbsUseCase
from calendar_engine.constants import DOMAIN_TIME_POLICY


class GetDomainSlotsUseCase(AbsUseCase):
    """Use-case для создания и показа клиенту на UI всех возможных доменных временных слотов (общее правило домена)
    для заданного в системе определенного количества ближайших дней (например, на ближайшие 7 дней: "DAYS_AHEAD = 7").
        Пример результата use-case:
          {
            "2026-01-16": ['2026-01-16T00:00:00+03:00', '2026-01-16T01:00:00+03:00', ...],
            "2026-01-17": [...]
          }
    """

    DAYS_AHEAD = 7

    def __init__(self, *, timezone):
        self.timezone = timezone

    def execute(self) -> dict:
        """Выполняет генерацию всех возможных доменных временных слотов."""
        # Получаем текущее время в timezone пользователя, где astimezone(self.timezone) - это метод, который
        # говорит: "И пересчитай это время для моего часового пояса".
        current_time = now().astimezone(self.timezone)
        today = current_time.date()

        slots_by_day: dict[str, list[str]] = {}

        for day_offset in range(self.DAYS_AHEAD):  # Цикл по последовательности чисел 0, 1, 2, 3, 4, 5, 6 (7 дней)
            day = today + timedelta(days=day_offset)

            day_slots = []

            # Берем дату и нарезаем ее на слоты ("09:00–10:00", "10:00–11:00", ...)
            for start_time, _ in DOMAIN_TIME_POLICY.iter_day_slots(day):
                start_dt = make_aware(
                    datetime.combine(day, start_time),  # Что тут происходит???
                    timezone=self.timezone,
                )

                # Фильтрация слотов, которая избавляет от показа "прошедших сегодня" и от рассинхрона UTC и local
                if start_dt < current_time:
                    continue

                day_slots.append(start_dt.isoformat())  # isoformat() превращает datetime объект-Python в СТРОКУ

            if day_slots:
                slots_by_day[str(day)] = day_slots

        return slots_by_day
