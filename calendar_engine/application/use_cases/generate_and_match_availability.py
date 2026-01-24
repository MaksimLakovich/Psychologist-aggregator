from datetime import date

from calendar_engine.application.use_cases.base import AbsUseCase
from calendar_engine.domain.availability.base import (AbsAvailabilityException,
                                                      AbsAvailabilityRule)
from calendar_engine.domain.availability.get_user_slots import \
    AvailabilitySlotFilter
from calendar_engine.domain.matching.base import AbsTimeMatcher
from calendar_engine.domain.matching.dto import MatchResultDTO
from calendar_engine.domain.time_policy.base import AbsDomainTimePolicy


class GenerateAndMatchAvailabilityUseCase(AbsUseCase):
    """Use-case генерации и matching доступных слотов специалиста.
    Отвечает за прикладной сценарий:
        1) генерация доступных слотов специалиста в заданном временном окне;
        2) применение matching-логики (через переданный matcher);
        3) возврат итогового результата.
    ВАЖНО:
        - use-case не знает, по каким критериям происходит matching;
        - критерии (период, выбранные слоты и т.п.) инкапсулированы в matcher;
        - date_from/date_to используются ТОЛЬКО как окно генерации."""

    def __init__(
        self,
        *,
        time_policy: AbsDomainTimePolicy,
        availability_rule: AbsAvailabilityRule,
        availability_exceptions: list[AbsAvailabilityException],
        matcher: AbsTimeMatcher,
    ) -> None:
        """
        :param time_policy: Доменная временная политика (шаг слота, границы дня).
        :param availability_rule: Индивидуальное правило доступности специалиста (базовое рабочее расписание).
        :param availability_exceptions: Индивидуальные исключения из правил доступности (отпуск, больничный).
        :param matcher: Доменный сервис matching - применяет клиентские предпочтения ко сгенерированным слотам.
        """
        self._time_policy = time_policy
        self._rule = availability_rule
        self._exceptions = availability_exceptions
        self._matcher = matcher

    def execute(self, *, date_from: date, date_to: date) -> MatchResultDTO:
        """Выполняет сценарий генерации и matching доступных слотов.

        :param date_from: Дата начала окна генерации доступности.
        :param date_to: Дата окончания окна генерации доступности.
        :return: MatchResultDTO - результат matching, определяемый matcher-ом."""

        # 1) Создание генератора доступности специалиста
        generator = AvailabilityGenerator(
            time_policy=self._time_policy,
            rule=self._rule,
            exceptions=self._exceptions,
        )

        # 2) Запуск метода по нарезке слотов в генераторе
        availability = generator.generate_slots(
            date_from=date_from,
            date_to=date_to,
        )

        # 3) Применение matching-логики
        return self._matcher.match(
            availability=availability,
            date_from=date_from,
            date_to=date_to,
        )
