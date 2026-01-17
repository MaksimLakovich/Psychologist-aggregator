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
            - задать границы доменного дня, которые общие для всех пользователей (сделать 24/7 или сделать 09:00–18:00)
            - уметь итерировать слоты дня"""

    def __init__(self, *, day_time_start: time, day_time_end: time, slot_duration_minutes: int,) -> None:
        """
        * - это защита от positional misuse, чтоб случайно не передать в day_time_start данные time для окончания дня
        и наоборот.
        Positional Misuse - это ситуация, когда разработчик путает порядок аргументов, потому что они передаются
        просто списком (позиционно).
        """
        if slot_duration_minutes <= 0:
            raise ValueError("slot_duration_minutes должно быть положительным значением.")

        self.day_time_start = day_time_start  # Начало дня
        self.day_time_end = day_time_end  # Конец дня (НЕ включительно)
        self.duration_slot = timedelta(minutes=slot_duration_minutes)  # Длительность одного базового слота (в минутах)

    def iter_day_slots(self, day: date) -> Iterable[Tuple[time, time]]:
        """Генерирует базовые слоты домена для одного дня:
            - Работает в доменном времени (TIME_ZONE проекта);
            - Это НЕ availability и НЕ бронирование;
            - Это базовая временная сетка домена - общие для всех пользователей (сделать 24/7 или сделать 09:00–18:00).
        Возвращает итератор пар (start, end) для одного календарного дня.
        Возвращаемые интервалы НЕ учитывают availability и бронирования."""

        current_day_start = datetime.combine(day, self.day_time_start)

        # Так как в текущем домене у нас НАЧАЛО_ДНЯ=time(0, 0) и КОНЕЦ_ДНЯ=time(0, 0), потому что мы генерируем
        # временную сетку под 24/7, а не "с 09-00 до 18-00", то чтоб генерился 24-й слот в сутках ('23:00:00')
        # нам нужно для 24-го слота сместить день +1
        if self.day_time_end <= self.day_time_start:
            current_day_end = datetime.combine(day + timedelta(days=1), self.day_time_end)
        else:
            current_day_end = datetime.combine(day, self.day_time_end)

        # Пока текущее время плюс длительность слота не вылезли за границу конца дня - то продолжаем
        while current_day_start + self.duration_slot <= current_day_end:
            start = current_day_start.time()
            end = (current_day_start + self.duration_slot).time()

            # yield - ленивая генерация. Вместо того чтобы создавать огромный список всех слотов в памяти,
            # функция выдает их по одному. Как только мы попросим следующий слот - она "проснется", и делает
            # один шаг цикла и снова замирает. Это очень экономно для памяти.
            yield start, end

            current_day_start += self.duration_slot
