from datetime import date, time
from typing import Iterable, List

from calendar_engine.domain.availability.base import (AbsAvailabilityException,
                                                      AbsAvailabilityRule)
from calendar_engine.domain.availability.dto import SlotDTO


class AvailabilitySlotFilter:
    """Фильтр всех возможных доменных слотов по индивидуальным правилам доступности специалиста.
    Т.е., учитываем рабочее расписание специалиста (рабочие окна) из индивидуальных правил доступности
    специалиста (AvailabilityRule) и индивидуальных исключений из правил (AvailabilityException).

    ВАЖНО:
        - класс НЕ генерирует слоты (он использует только доменные слоты и фильтрует их под правила специалиста);
        - класс НЕ знает про диапазоны дат;
        - класс НЕ знает про БД, пользователей, UI;
        - класс работает ТОЛЬКО с готовыми SlotDTO (ранее сгенерированные доменные слоты).
    Ответственность:
        Взять доменные слоты и оставить только те, которые разрешены AvailabilityRule и AvailabilityException."""

    def __init__(self, *, rule: AbsAvailabilityRule, exceptions: Iterable[AbsAvailabilityException] = ()) -> None:
        """
        * - это защита от positional misuse, чтоб случайно не передать в аргументы неправильный набор данных.
        Positional Misuse - это ситуация, когда разработчик путает порядок аргументов, потому что они передаются
        просто списком (позиционно).

        :param rule: Индивидуальное правило доступности специалиста (базовое рабочее расписание).
        :param exceptions: Исключения из правил (отпуск, больничный, особые дни).
        """
        self._rule = rule
        self._exceptions = tuple(exceptions)

    def _get_user_time_windows(self, day: date) -> List[tuple[time, time]]:
        """Возвращает итоговые разрешенные временные окна для конкретного дня с учетом приоритета исключений.
        Логика:
            1) Если есть применимое исключение - оно ПОЛНОСТЬЮ переопределяет правило.
            2) Если исключений нет - используется базовое правило.
            3) Если день нерабочий - возвращается пустой список.
        Результат:
            None - ни одно исключение не применилось;
            [] - день полностью закрыт;
            tuple[time, time] - переопределенные рабочие окна."""

        # 1) Проверяем наличие действующих исключений в правиле (имеют приоритет) и если есть действующее
        # исключение - используем правило из AbsAvailabilityException для переопределения временных окон внутри дня
        for exception in self._exceptions:
            overridden = exception.override_time_windows(day)
            if overridden is not None:
                return list(overridden)

        # 2) Если исключений нет - используем базовое правило из AbsAvailabilityRule для формирования разрешенных
        # временных периодов специалиста внутри дня, в которые он работает (например, "09:00–19:00")
        return list(self._rule.iter_time_windows(day))

    def filter_user_slots(self, *, domain_slots: Iterable[SlotDTO]) -> List[SlotDTO]:
        """Фильтрует все возможные доменные слоты по индивидуальным правилам доступности специалиста.

        :param domain_slots: Готовые доменные слоты (из DomainSlotGenerator).
        :return: Подмножество SlotDTO, доступные для данного специалиста."""

        allowed_slots: List[SlotDTO] = []

        for slot in domain_slots:
            day = slot.day

            # 1) Получаем разрешенные временные окна дня
            time_windows = self._get_user_time_windows(day)

            if not time_windows:
                continue  # День полностью закрыт

            # 2) Проверяем, попадает ли слот в любое разрешенное окно
            for window_start, window_end in time_windows:
                if (
                        slot.start >= window_start and slot.end <= window_end
                ):
                    allowed_slots.append(slot)
                    break  # слот уже принят, дальше окна проверять не нужно

        return allowed_slots
