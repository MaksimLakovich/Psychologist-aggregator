from datetime import date, time
from typing import Iterable

from calendar_engine.application.mappers.availability_rule_mapper import \
    map_availability_rule_to_domain
from calendar_engine.application.use_cases.generate_and_match_availability import \
    GenerateAndMatchAvailabilityUseCase
from calendar_engine.constants import DOMAIN_TIME_POLICY
from calendar_engine.domain.matching.matcher import SelectedSlotsMatcher
from calendar_engine.models import AvailabilityException, AvailabilityRule


def build_generate_and_match_use_case(*, psychologist, selected_slots: Iterable[tuple[date, time, time]]):
    """Собирает use-case генерации и matching доступности для одного психолога.
    :param psychologist: пользователь с psychologist_profile
    :param selected_slots: доменные слоты, выбранные клиентом (date, start_time, end_time)
    :return: GenerateAndMatchAvailabilityUseCase или None, если у психолога нет активного AvailabilityRule"""

    rule = AvailabilityRule.objects.filter(
        creator=psychologist,
        is_active=True,
    ).first()

    if not rule:
        return None

    exceptions = AvailabilityException.objects.filter(
        rule=rule,
        is_active=True,
    )

    matcher = SelectedSlotsMatcher(
        selected_slots=selected_slots,
    )

    # Адаптирует django-объект AvailabilityRule в доменное правило доступности, без этой адаптации получаем ошибку
    domain_rule = map_availability_rule_to_domain(rule)

    return GenerateAndMatchAvailabilityUseCase(
        time_policy=DOMAIN_TIME_POLICY,
        availability_rule=domain_rule,
        availability_exceptions=list(exceptions),
        matcher=matcher,
    )
