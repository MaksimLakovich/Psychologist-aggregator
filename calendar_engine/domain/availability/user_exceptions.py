from datetime import date, time
from typing import Iterable, Optional, Tuple

from calendar_engine.domain.availability.base import AbsAvailabilityException


class DateAvailabilityException(AbsAvailabilityException):
    """Исключение для конкретной даты.
    Используется для:
        - выходного дня;
        - отпуска;
        - больничного;
        - праздника."""

    def __init__(self, *, day: date) -> None:
        """
        * - это защита от positional misuse, чтоб случайно не передать в time_windows данные Tuple[time, time]
        с неправильным набором (вначале конец, а потом начало).
        Positional Misuse - это ситуация, когда разработчик путает порядок аргументов, потому что они передаются
        просто списком (позиционно).
        """
        self._day = day

    def applies_to_day(self, day: date) -> bool:
        """Метод проверяет - применяется ли исключение к указанной дате."""
        return day == self._day

    def override_time_windows(self) -> Optional[Iterable[Tuple[time, time]]]:
        """Метод возвращает временные окна внутри дня, в которые специалист работает по правилам исключения:
            - None: день полностью закрыт (day-off)."""
        return None


class DayAvailabilityException(AbsAvailabilityException):
    """Переопределение рабочих окон конкретного дня (сокращенный или особый день).
    Пример: 31 декабря: 09:00–15:00."""

    def __init__(self, *, day: date, time_windows: Iterable[Tuple[time, time]]) -> None:
        """
        * - это защита от positional misuse, чтоб случайно не передать в time_windows данные Tuple[time, time]
        с неправильным набором (вначале конец, а потом начало).
        Positional Misuse - это ситуация, когда разработчик путает порядок аргументов, потому что они передаются
        просто списком (позиционно).

        :param day: Конкретный календарный день.

        :param time_windows: Итерируемый набор временных окон (start_time, end_time) внутри заданного календарного дня.
        """
        validated_windows = []

        for start, end in time_windows:
            if start >= end:
                raise ValueError(
                    f"Некорректное временное окно: {start} >= {end}"
                )
            validated_windows.append((start, end))

        if not validated_windows:
            raise ValueError("time_windows не может быть пустым")

        self._day = day
        self._time_windows = tuple(validated_windows)

    def applies_to_day(self, day: date) -> bool:
        """Метод проверяет - применяется ли исключение к указанной дате."""
        return day == self._day

    def override_time_windows(self) -> Optional[Iterable[Tuple[time, time]]]:
        """Метод возвращает новые временные окна внутри дня, в которые специалист работает по правилам исключения:
            - Iterable[(start, end)]: новые временные окна дня."""
        return self._time_windows
