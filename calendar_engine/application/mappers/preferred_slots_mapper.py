from datetime import date, datetime, time
from typing import Iterable, List, Tuple, Union

RawSlot = Union[str, datetime]

SelectedSlotKey = Tuple[date, time]


def map_preferred_slots_to_domain(preferred_slots: Iterable[RawSlot]) -> List[SelectedSlotKey]:
    """Адаптирует preferred_slots в доменный формат matcher-а.

    ИНФО:
        1) Поддерживаемые форматы входных данных:
            - datetime (основной runtime-кейс);
            - str в ISO-формате (legacy / миграции / тесты).
        2) В БД слоты хранятся как строки datetime: "2026-01-22 19:00:00+03";
        3) end_time здесь не используется;
        4) шаг слота и длительность определяются доменной time_policy.
    """
    result: List[SelectedSlotKey] = []

    for raw_value in preferred_slots:
        if isinstance(raw_value, datetime):
            dt = raw_value
        elif isinstance(raw_value, str):
            dt = datetime.fromisoformat(raw_value)
        else:
            raise TypeError(
                f"Неподдерживаемый тип данных в preferred_slot: {type(raw_value)!r}"
            )

        result.append(
            (dt.date(), dt.time())
        )

    return result
