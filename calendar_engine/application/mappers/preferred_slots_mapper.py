from datetime import datetime
from typing import Iterable, List, Union

RawSlot = Union[str, datetime]


def map_preferred_slots_to_domain(preferred_slots: Iterable[RawSlot]) -> List[datetime]:
    """Адаптирует preferred_slots в доменный формат matcher-а, СОХРАНЯЯ timezone.

    ИНФО:
        - возвращаем timezone-aware datetime;
        - в БД слоты хранятся как строки datetime: "2026-01-22 19:00:00+03";
        - никакого .date() / .time() здесь больше нет;
        - шаг слота и длительность определяются доменной time_policy.
    """
    result: List[datetime] = []

    for raw_value in preferred_slots:
        if isinstance(raw_value, datetime):
            dt = raw_value
        elif isinstance(raw_value, str):
            dt = datetime.fromisoformat(raw_value)
        else:
            raise TypeError(
                f"Неподдерживаемый тип данных в preferred_slot: {type(raw_value)!r}"
            )

        if dt.tzinfo is None:
            raise ValueError(
                "preferred_slot должен быть timezone-aware datetime"
            )

        result.append(dt)

    return result
