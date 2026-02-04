from zoneinfo import ZoneInfo

from django.utils.timezone import now

from calendar_engine.application.mappers.exception_mapper import \
    map_exceptions_to_domain
from calendar_engine.application.mappers.rule_mapper import map_rule_to_domain
from calendar_engine.application.use_cases.specialist_schedule import \
    GenerateSpecialistScheduleUseCase
from calendar_engine.constants import DAYS_AHEAD_FOR_SHOW_SCHEDULE
from calendar_engine.domain.availability.domain_slot_generator import \
    DomainSlotGenerator
from calendar_engine.domain.availability.get_user_slots import \
    AvailabilitySlotFilter
from calendar_engine.models import AvailabilityException, AvailabilityRule
from users.models import PsychologistProfile


def build_generate_specialist_schedule_use_case(
        specialist_profile: PsychologistProfile
) -> GenerateSpecialistScheduleUseCase | None:
    """Factory сборки use-case генерации расписания специалиста.
    Возвращает:
        - use-case, если у специалиста есть активное правило;
        - None, если специалист сейчас недоступен.

    :param specialist_profile: На вход именно объект будет поступать в эту функцию из "/api/match-psychologists/".
    :return:
        - GenerateSpecialistScheduleUseCase - если у специалиста есть актуальное расписание;
        - None - если правило отсутствует (специалист недоступен)."""

    # 1) Получаем активное правило доступности специалиста
    rule = (
        AvailabilityRule.objects
        .filter(
            creator=specialist_profile.user,
            is_active=True,
        )
        .first()
    )

    # Без активного правила специалист считается недоступным
    if rule is None:
        return None

    # 2) Получаем все активные исключения для этого правила
    exceptions = AvailabilityException.objects.filter(
        rule=rule,
        is_active=True,
    )

    # 3) Адаптируем Django-модели → доменные объекты
    domain_rule = map_rule_to_domain(rule)
    domain_exceptions = map_exceptions_to_domain(exceptions)

    # 4) Фильтруем все возможные доменные слоты по индивидуальным правилам доступности специалиста
    slot_filter = AvailabilitySlotFilter(
        rule=domain_rule,
        exceptions=domain_exceptions,
    )

    # 5) Определяем дату старта генерации В timezone СПЕЦИАЛИСТА, где astimezone(self.timezone) - это метод, который
    # говорит: "И пересчитай это время для данного часового пояса".
    specialist_timezone = getattr(specialist_profile.user, "timezone", None)
    if specialist_timezone:
        specialist_tz = ZoneInfo(str(specialist_timezone))
        current_specialist_time = now().astimezone(specialist_tz)
    else:
        current_specialist_time = now()
    date_from = current_specialist_time.date()

    # 6) Генератор доменных слотов
    slot_generator = DomainSlotGenerator()

    # 7) Финальная сборка use-case
    return GenerateSpecialistScheduleUseCase(
        slot_generator=slot_generator,
        slot_filter=slot_filter,
        date_from=date_from,
        days_ahead=DAYS_AHEAD_FOR_SHOW_SCHEDULE,
    )
