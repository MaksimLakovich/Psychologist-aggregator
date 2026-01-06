from datetime import date, time, timedelta
from typing import Iterable, List

from calendar_engine.domain.availability.base import (AbsAvailabilityException,
                                                      AbsAvailabilityRule)
from calendar_engine.domain.availability.dto import (AvailabilityDayDTO,
                                                     AvailabilityDTO, SlotDTO)
from calendar_engine.domain.time_policy.base import AbsDomainTimePolicy


class AvailabilityGenerator:
    """Генератор доступных слотов специалиста (on-the-fly).

    Объединяет в себе:
        - доменную временную сетку (DomainTimePolicy);
        - индивидуальные правила доступности специалиста (AvailabilityRule);
        - индивидуальные исключения из правил (AvailabilityException).

    Генератор:
        - НЕ знает ничего про БД;
        - НЕ знает ничего про пользователей, специалистов, клиентов;
        - НЕ знает ничего про бронирования;
        - работает исключительно с domain-объектами.
    """

    def __init__(
        self,
        *,
        time_policy: AbsDomainTimePolicy,
        rule: AbsAvailabilityRule,
        exceptions: Iterable[AbsAvailabilityException] = (),
    ) -> None:
        """
        * - это защита от positional misuse, чтоб случайно не передать в аргументы неправильный набор данных.
        Positional Misuse - это ситуация, когда разработчик путает порядок аргументов, потому что они передаются
        просто списком (позиционно).

        :param time_policy: Контракт доменной временной сетки (шаг слота, границы дня).
        :param rule: Индивидуальное правило доступности специалиста (базовое рабочее расписание).
        :param exceptions: Исключения из правил (отпуск, больничный, особые дни).
        """
        self._time_policy = time_policy
        self._rule = rule
        self._exceptions = tuple(exceptions)

    def _apply_exceptions(self, day: date) -> Iterable[tuple[time, time]] | None:
        """Проверяет и применяет исключения к конкретному дню.

        :param day: Определенный календарный день.
        :return:
            - None -> ни одно исключение не применилось;
            - [] -> день полностью закрыт;
            - Iterable[(start, end)] -> переопределённые рабочие окна."""
        for exception in self._exceptions:
            result = exception.override_time_windows(day)
            if result is not None:
                return result

        return None

    def _slice_window_to_slots(self, *, day: date, window_start: time, window_end: time) -> List[SlotDTO]:
        """Нарезает рабочее окно дня в доменные слоты. Использует ТОЛЬКО доменную временную сетку.

        :param day: Определенный календарный день.
        :param window_start: Начало рабочего дня.
        :param window_end: Окончание рабочего дня.
        :return: DTO - объект, предназначенный только для транспортировки данных между слоями/частями приложения."""
        slots: List[SlotDTO] = []

        for slot_start, slot_end in self._time_policy.iter_day_slots(day):
            # Слот должен полностью помещаться в рабочее окно
            if slot_start < window_start:
                continue
            if slot_end > window_end:
                continue

            slots.append(
                SlotDTO(
                    day=day,
                    start=slot_start,
                    end=slot_end,
                )
            )

        return slots

    def _generate_day(self, day: date) -> AvailabilityDayDTO:
        """Генерирует доступные слоты для одного рабочего дня по персональным правилам специалиста.

        :param day: Определенный день.
        :return: DTO - объект, предназначенный только для транспортировки данных между слоями/частями приложения."""

        # 1) Проверяем исключения (они имеют приоритет над правилами)
        override_windows = self._apply_exceptions(day)

        if override_windows is None:
            # 2) Если исключения не применились - используем базовое правило
            working_windows = list(self._rule.iter_time_windows(day))
        else:
            # override_windows может быть:
            #   [] -> день полностью закрыт
            #   [...] -> переопределенные окна
            working_windows = list(override_windows)

        # 3) Нарезаем рабочие окна на доменные слоты
        slots: List[SlotDTO] = []

        for window_start, window_end in working_windows:
            slots.extend(
                self._slice_window_to_slots(
                    day=day,
                    window_start=window_start,
                    window_end=window_end,
                )
            )

        return AvailabilityDayDTO(day=day, slots=slots)

    def generate_slots(self, *, date_from: date, date_to: date) -> AvailabilityDTO:
        """Генерирует доступные слоты в диапазоне дат [date_from, date_to] включительно.
        Это внутренний API (то есть API доменного слоя, а не HTTP).

        :param date_from: Дата начала периода.
        :param date_to: Дата окончания периода.
        :return: DTO - объект, предназначенный только для транспортировки данных между слоями/частями приложения."""
        if date_from > date_to:
            raise ValueError("date_from не может быть позже date_to")

        days: List[AvailabilityDayDTO] = []

        current_day = date_from
        while current_day <= date_to:
            days.append(self._generate_day(current_day))
            current_day += timedelta(days=1)

        return AvailabilityDTO(days=days)
