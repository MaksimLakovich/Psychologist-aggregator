from datetime import date, time
from typing import Iterable, Optional, Tuple

from calendar_engine.domain.availability.base import AbsAvailabilityException


class DateAvailabilityException(AbsAvailabilityException):
    """Исключение для конкретной даты.
    Используется для:
        - отпуска;
        - больничного;
        - праздника."""

    def __init__(self, *, day: date) -> None:
        """
        * - это защита от positional misuse, чтоб случайно не передать в time_windows данные Tuple[time, time]
        с неправильным набором (вначале конец, а потом начало).
        Positional Misuse - это ситуация, когда разработчик путает порядок аргументов, потому что они передаются
        просто списком (позиционно).

        :param day: Конкретный рабочий день.
        """
        self._day = day

    def override_time_windows(self, day: date) -> Optional[Iterable[Tuple[time, time]]]:
        """Метод проверяет - применяется ли исключение к указанной дате и если да, то возвращает пустой список,
        что означает отсутствие временных слотов на данный день:
            - []: день полностью закрыт (day-off);
            - None: исключение НЕ применяется к этому дню."""
        if day == self._day:
            return []
        return None


class TimeAvailabilityException(AbsAvailabilityException):
    """Переопределение рабочих окон конкретного дня (сокращенный или особый день).
    Пример: 31 декабря: 09:00–15:00."""

    def __init__(self, *, day: date, time_windows: Iterable[Tuple[time, time]]) -> None:
        """
        * - это защита от positional misuse, чтоб случайно не передать в time_windows данные Tuple[time, time]
        с неправильным набором (вначале конец, а потом начало).
        Positional Misuse - это ситуация, когда разработчик путает порядок аргументов, потому что они передаются
        просто списком (позиционно).

        :param day: Конкретный рабочий день.
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

    def override_time_windows(self, day: date) -> Optional[Iterable[Tuple[time, time]]]:
        """Метод проверяет - применяется ли исключение к указанной дате и если да, то возвращает
        новые временные окна внутри дня, в которые специалист работает по правилам исключения:
            - Iterable[(start, end)]: новые временные окна дня;
            - None: исключение НЕ применяется к этому дню."""
        if day == self._day:
            return self._time_windows
        return None
