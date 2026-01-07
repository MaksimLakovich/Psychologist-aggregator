from datetime import date

from calendar_engine.application.use_cases.base import AbsUseCase
from calendar_engine.domain.availability.base import (AbsAvailabilityException,
                                                      AbsAvailabilityRule)
from calendar_engine.domain.availability.generator import AvailabilityGenerator
from calendar_engine.domain.matching.base import AbsTimeMatcher
from calendar_engine.domain.matching.dto import MatchResultDTO
from calendar_engine.domain.time_policy.base import AbsDomainTimePolicy


class GenerateAndMatchAvailabilityUseCase(AbsUseCase):
    """Use-case генерации и matching доступных слотов специалиста.

    Отвечает за прикладной сценарий:
        1) генерация доступных слотов по правилам специалиста;
        2) применение matching-логики (предпочтения клиента, фильтры);
        3) возврат итогового результата.

    НЕ содержит бизнес-логики:
        - вся логика находится в domain-слое."""

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

        :param date_from: Дата начала интересующего периода.
        :param date_to: Дата окончания интересующего периода.
        :return: MatchResultDTO - итоговый результат, готовый к использованию во внешних слоях (aggregator, UI)."""

        # 1) Генерация доступности специалиста
        generator = AvailabilityGenerator(
            time_policy=self._time_policy,
            rule=self._rule,
            exceptions=self._exceptions,
        )

        availability = generator.generate_slots(
            date_from=date_from,
            date_to=date_to,
        )

        # 2) Применение matching-логики
        return self._matcher.match(
            availability=availability,
            date_from=date_from,
            date_to=date_to,
        )
