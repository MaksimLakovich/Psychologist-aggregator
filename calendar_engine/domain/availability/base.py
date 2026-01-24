from abc import ABC, abstractmethod
from datetime import date, time
from typing import Iterable, Optional, Tuple


class AbsAvailabilityRule(ABC):
    """Абстрактный контракт индивидуального правила доступности специалиста (рабочее расписание).
    AvailabilityRule:
        - определяет ВРЕМЕННЫЕ ОКНА, в которые специалист МОЖЕТ работать;
        - применяется поверх доменной временной сетки;
        - не знает ничего про: бронирования, исключения, клиентов, UI."""

    @abstractmethod
    def iter_time_windows(self, day: date) -> Iterable[Tuple[time, time]]:
        """Возвращает разрешенные временные периоды внутри дня, в которые специалист работает (например 09:00–12:00):
            - Iterable[(start, end)]: временные окна внутри рабочего дня;
            - пустой iterable: нерабочий день возвращает пустой iterable.
        ВАЖНО:
            - это НЕ слоты;
            - это НЕ доменная сетка;
            - это разрешенные интервалы."""
        raise NotImplementedError


class AbsAvailabilityException(ABC):
    """Абстрактный контракт исключения из правил доступности специалиста.
    AvailabilityException:
        - применяется к конкретной дате или диапазону дат;
        - имеет приоритет над AvailabilityRule;
        - может:
            - полностью закрыть день/дни;
            - или переопределить рабочие окна дня."""

    @abstractmethod
    def override_time_windows(self, day: date) -> Optional[Iterable[Tuple[time, time]]]:
        """Возвращает новые временные окна внутри дня, в которые специалист работает по правилам исключения:
            - None: исключение НЕ применяется к этому дню;
            - []: день полностью закрыт (day-off);
            - Iterable[(start, end)]: правило полностью переопределено (заданы новые временные окна дня)."""
        raise NotImplementedError
