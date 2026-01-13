from datetime import date, time
from typing import Iterable

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

    return GenerateAndMatchAvailabilityUseCase(
        time_policy=DOMAIN_TIME_POLICY,
        availability_rule=rule,
        availability_exceptions=list(exceptions),
        matcher=matcher,
    )
