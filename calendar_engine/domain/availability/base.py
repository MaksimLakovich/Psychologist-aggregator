from abc import ABC, abstractmethod
from datetime import date, time
from typing import Iterable, Optional, Tuple


class AbsAvailabilityRule(ABC):
    """Абстрактный контракт индивидуального правила доступности специалиста (рабочее расписание).
    AvailabilityRule:
        - определяет ВРЕМЕННЫЕ ОКНА, в которые специалист МОЖЕТ работать;
        - применяется поверх доменной временной сетки;
        - не знает ничего про: бронирования, исключения, клиентов, UI."""

    # Декоратор, который помечает метод как "обязательный". Если создать дочерний класс и забыть написать там
    # этот метод, то Python не позволит создать экземпляр этого класса.
    @abstractmethod
    def applies_to_day(self, day: date) -> bool:
        """Метод проверяет - применяется ли правило к конкретной календарной дате.
        Например:
            - только по понедельникам;
            - только по будням;
            - только в определенный диапазон дат."""
        raise NotImplementedError

    @abstractmethod
    def iter_time_windows(self) -> Iterable[Tuple[time, time]]:
        """Метод возвращает временные окна внутри дня, в которые специалист работает (например 09:00–12:00).
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
    def applies_to_day(self, day: date) -> bool:
        """Метод проверяет - применяется ли исключение к указанной дате/датам."""
        raise NotImplementedError

    @abstractmethod
    def override_time_windows(self) -> Optional[Iterable[Tuple[time, time]]]:
        """Метод возвращает новые временные окна внутри дня, в которые специалист работает по правилам исключения:
            - None: день полностью закрыт (day-off);
            - Iterable[(start, end)]: новые временные окна дня."""
        raise NotImplementedError
