from datetime import datetime, date, time
from typing import Iterable, List, Tuple

SelectedSlotKey = Tuple[date, time]


def map_preferred_slots_to_domain(preferred_slots: Iterable[str]) -> List[SelectedSlotKey]:
    """Адаптирует preferred_slots из БД в доменный формат matcher-а.

    ИНФО:
        1) В БД слоты хранятся как строки datetime: "2026-01-22 19:00:00+03"
        2) Matcher работает ТОЛЬКО с: (day, start_time)
        3) end_time здесь принципиально не используется, так как:
            - он известен доменной политике;
            - пользователь его не выбирает.
    """
    result: List[SelectedSlotKey] = []

    for raw_value in preferred_slots:
        dt = datetime.fromisoformat(raw_value)
        result.append(
            (dt.date(), dt.time())
        )

    return result
