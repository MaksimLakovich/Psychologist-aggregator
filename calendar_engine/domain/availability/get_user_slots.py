from datetime import date, datetime, time, timedelta
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

        def normalize_range(day: date, start: time, end: time) -> tuple[datetime, datetime]:
            """Нужно сравнивать datetime, а не time, чтобы корректно учитывать интервалы, пересекающие границу суток.
            - исключает ситуации, когда 'end < start' и интервал фактически "ломается" (это проблема для слотов
              с 'end = 00:00' и 'start = 23:00', где получалось что end больше start и получаем баг).
            - для этого выполняем нормализацию диапазонов в datetime и если 'end <= start' - то считается,
              что диапазон пересекает полночь и нужно добавить +1 день."""
            start_dt = datetime.combine(day, start)
            end_dt = datetime.combine(day, end)

            if end <= start:
                end_dt += timedelta(days=1)

            return start_dt, end_dt

        # 1) Получаем разрешенные временные окна дня
        allowed_slots: List[SlotDTO] = []

        for slot in domain_slots:
            day = slot.day  # получаем день из доменных слотов
            time_windows = self._get_user_time_windows(day)  # получаем временные окна для конкретного дня

            if not time_windows:
                continue  # день полностью закрыт и идем дальше

            # ПЕРЕД ТЕМ КАК НАЧАТЬ ПРОВЕРЯТЬ ВХОЖДЕНИЕ СЛОТА ВО ВРЕМЕННОЕ ОКНО - ВЫПОЛНЯЕМ НОРМАЛИЗАЦИЮ
            slot_start_dt, slot_end_dt = normalize_range(
                day, slot.start, slot.end
            )

            # 2) Проверяем, попадает ли слот в любое разрешенное окно
            for window_start, window_end in time_windows:
                window_start_dt, window_end_dt = normalize_range(
                    day, window_start, window_end
                )

                if slot_start_dt >= window_start_dt and slot_end_dt <= window_end_dt:
                    allowed_slots.append(slot)
                    break  # слот уже принят, дальше окна проверять не нужно

        return allowed_slots
