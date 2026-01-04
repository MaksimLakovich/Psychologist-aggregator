from datetime import date, datetime, time, timedelta
from typing import Iterable, Tuple

from calendar_engine.domain.time_policy.base import AbsDomainTimePolicy


class DomainTimePolicy(AbsDomainTimePolicy):
    """Доменная временная сетка.
        Пример:
            - слот: 60 минут или 30 минут
            - день: 09:00–21:00 или 00:00-23-59
        Она НЕ знает ничего про:
            - пользователей
            - availability
            - бронирования
            - события
        Ее задача:
            - задать шаг времени (slot size)
            - задать границы дня (сделать 24/7 или сделать 09:00–18:00)
            - уметь итерировать слоты дня
    """

    def __init__(self, *, day_time_start: time, day_time_end: time, slot_duration_minutes: int,) -> None:
        """
        * - это защита от positional misuse
        """
        if slot_duration_minutes <= 0:
            raise ValueError("slot_duration_minutes должно быть положительным значением.")

        if day_time_start >= day_time_end:
            raise ValueError("day_time_end не может быть раньше day_time_start")

        self.day_time_start = day_time_start  # Начало календарного дня
        self.day_time_end = day_time_end  # Конец календарного дня (НЕ включительно)
        self.duration_slot = timedelta(minutes=slot_duration_minutes)  # Длительность одного базового слота (в минутах)

    def iter_day_slots(self, day: date) -> Iterable[Tuple[time, time]]:
        """Генерирует базовые слоты домена для одного дня:
            - Работает в доменном времени (TIME_ZONE проекта);
            - Это НЕ availability и НЕ бронирование;
            - Это базовая временная сетка домена.
        Возвращает итератор пар (start, end) для одного календарного дня.
        Возвращаемые интервалы НЕ учитывают availability и бронирования."""

        current_day_start = datetime.combine(day, self.day_time_start)
        current_day_end = datetime.combine(day, self.day_time_end)

        while current_day_start + self.duration_slot <= current_day_end:
            start = current_day_start.time()
            end = (current_day_start + self.duration_slot).time()

            yield start, end  # ленивая генерация

            current_day_start += self.duration_slot
