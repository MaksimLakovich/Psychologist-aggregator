from datetime import date, time
from typing import Iterable, Set, Tuple

from calendar_engine.domain.availability.base import AbsAvailabilityRule


class WeeklyAvailabilityRule(AbsAvailabilityRule):
    """Индивидуальное правило доступности специалиста по дням недели (рабочее расписание).
    Пример:
        - работает по понедельникам и средам;
        - с 09:00 до 12:00;
        - и с 14:00 до 18:00."""

    def __init__(self, *, weekdays: Set[int], time_windows: Iterable[Tuple[time, time]]) -> None:
        """
        * - это защита от positional misuse, чтоб случайно не передать в time_windows данные Tuple[time, time]
        с неправильным набором (вначале конец, а потом начало).
        Positional Misuse - это ситуация, когда разработчик путает порядок аргументов, потому что они передаются
        просто списком (позиционно).

        :param weekdays: Набор дней недели, где:
            0 = Monday
            6 = Sunday
            (соответствует datetime.date.weekday())
        :param time_windows: Итерируемый набор временных окон (start_time, end_time) внутри одного рабочего дня.
        """

        if not weekdays:
            raise ValueError("weekdays не может быть пустым")

        validated_windows = []

        for start, end in time_windows:
            if start == end and start != time(0, 0):
                raise ValueError(
                    "Некорректное временное окно: равные start/end допускаются только для 24/7 (00:00–00:00)"
                )
            elif start > end:
                raise ValueError(f"Некорректное временное окно: {start} > {end}")
            validated_windows.append((start, end))

        if not validated_windows:
            raise ValueError("time_windows не может быть пустым")

        self._weekdays = weekdays
        self._time_windows = tuple(validated_windows)

    def iter_time_windows(self, day: date) -> Iterable[Tuple[time, time]]:
        """Метод проверяет - применяется ли правило к указанной дате на основе дня недели, то есть отвечает
        на вопрос "Работает ли специалист в конкретный день недели?" и возвращает доступные временные окна этого дня.

        1) yield превращает функцию в генератор. Вместо того чтобы вернуть все сразу (как return), функция как бы
        "приостанавливается" на каждом значении и отдает его по запросу;
        2) Конструкция "yield from" это по сути тоже самое что:
            for window in self._time_windows:
                yield window
        3) Дословно это означает: "Возьми коллекцию self._time_windows и по очереди выдай каждый элемент, который
        в ней лежит".
        4) Зачем нужен yield from, а не просто return?
            - Инкапсуляция: мы не отдаем саму внутреннюю структуру данных (список или кортеж). Мы отдаем "инструмент"
              для перебора этих данных.
            - Единообразие: если завтра мы решим изменить хранение окон (например, с кортежа на сложный объект), то
              логика перебора для пользователя останется прежней.
            - Безопасность: получая генератор, вызывающий код не сможет случайно изменить ваш внутренний
            кортеж self._time_windows (например, через pop или append), так как генератор позволяет только читать."""

        # 1) day.weekday() - это встроенный метод Python, который берет дату и вычисляет, какой это день недели
        # в числовом формате: если это понедельник, метод вернет 0, если вторник - 1, ... , если воскресенье - 6.
        # 2) Это "белый список" дней недели, который был сохранен в объекте при его создании (в методе __init__).
        # Например, если специалист работает только по понедельникам и средам, то внутри self._weekdays будет: {0, 2}.
        if day.weekday() not in self._weekdays:
            return
        yield from self._time_windows
