from datetime import datetime, timedelta
from typing import Dict, List

from django.utils.timezone import make_aware, now

from calendar_engine.application.use_cases.base import AbsUseCase
from calendar_engine.constants import DOMAIN_TIME_POLICY


class GetDomainSlotsUseCase(AbsUseCase):
    """Use-case для создания и показа клиенту на UI всех возможных доменных ВРЕМЕННЫХ СЛОТОВ (общее правило домена)
    для заданного в системе определенного количества дней (например, на ближайшие 7 дней: "DAYS_AHEAD = 7").

    ВАЖНО:
    - DOMAIN_TIME_POLICY работает без какого-либо timezone
    - timezone применяется ТОЛЬКО на уровне application/use-case
    - все возвращаемые слоты будут в timezone клиента

    Пример результата use-case:
        {
            '2026-01-16': ['2026-01-16T00:00:00+03:00', '2026-01-16T01:00:00+03:00', ...],
            '2026-01-17': [...]
        }
    """

    DAYS_AHEAD = 7

    def __init__(self, *, timezone):
        if timezone is None:
            raise ValueError("timezone обязателен для генерации доменных слотов")
        self.timezone = timezone

    def execute(self) -> Dict:
        """Выполняет генерацию всех возможных доменных временных слотов."""
        # ШАГ 1: Получаем текущее время в timezone КЛИЕНТА, где astimezone(self.timezone) - это метод, который
        # говорит: "И пересчитай это время для моего часового пояса".
        current_time = now().astimezone(self.timezone)
        today = current_time.date()

        slots_by_day: Dict[str, List[str]] = {}

        # ШАГ 2: Генерируем доменные слоты для КАЛЕНДАРНОГО ДНЯ клиента.
        # Запускаем цикл по последовательности чисел (DAYS_AHEAD: 7 дней): 0, 1, 2, 3, 4, 5, 6
        for day_offset in range(self.DAYS_AHEAD):
            day = today + timedelta(days=day_offset)

            day_slots: List[str] = []

            # Берем дату и нарезаем ее на слоты ('2026-01-16T00:00:00+03:00', '2026-01-16T01:00:00+03:00', ...)
            for start_time, _ in DOMAIN_TIME_POLICY.iter_day_slots(day):
                start_dt = make_aware(
                    datetime.combine(day, start_time),
                    timezone=self.timezone,
                )

                day_slots.append(start_dt.isoformat())  # isoformat() превращает datetime объект-Python в СТРОКУ

            if day_slots:
                slots_by_day[str(day)] = day_slots

        # ВАЖНО: кроме сгенерированных слотов (slots_by_day) нам необходимо передать на фронт еще текущее время
        # пользователя (now_iso), потому что определять его по времени сервера неправильно. Так как клиент в
        # настройках своего профиля указывает свой timezone и он может отличаться от сервера (путешествует например).
        # ОБОСНОВАНИЕ: текущее время пользователя нам необходимо для того, чтоб потом на странице деактивировать
        # слоты, которые уже в прошлом (делать их недоступными к выбору).
        return {
            "now_iso": current_time.isoformat(),
            "slots": slots_by_day,
        }
