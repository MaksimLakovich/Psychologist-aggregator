from datetime import date, time, tzinfo
from typing import Iterable, Optional, Tuple
from zoneinfo import ZoneInfo

from calendar_engine.application.mappers.exception_mapper import \
    map_exceptions_to_domain
from calendar_engine.application.mappers.rule_mapper import map_rule_to_domain
from calendar_engine.application.use_cases.filter_and_match_availability import \
    FilterAndMatchSlotsUseCase
from calendar_engine.domain.availability.get_user_slots import \
    AvailabilitySlotFilter
from calendar_engine.domain.matching.matcher import SelectedSlotsMatcher
from calendar_engine.models import AvailabilityException, AvailabilityRule

# Тип ключа выбранного пользователем доменного слота: (day, start_time)
# matcher работает ТОЛЬКО с этим типом
SlotKey = Tuple[date, time]


def build_generate_and_match_use_case(
    *,
    psychologist,
    selected_slots: Iterable,  # iterable[datetime] (aware)
) -> Optional[FilterAndMatchSlotsUseCase]:
    """Собирает application use-case фильтрации и matching доменных временных слотов для конкретного специалиста.

    Что делает factory:
        1) загружает активное правило доступности специалиста из БД;
        2) загружает связанные активные исключения;
        3) адаптирует Django-модели в доменные объекты (rules + exceptions);
        4) собирает AvailabilitySlotFilter;
        5) собирает SelectedSlotsMatcher;
        6) возвращает готовый FilterAndMatchSlotsUseCase.

    ВАЖНО:
        - factory НЕ генерирует доменные слоты;
        - factory НЕ выполняет use-case;
        - factory НЕ содержит бизнес-логики;
        - factory только связывает компоненты.

    :param psychologist: Пользователь с psychologist_profile.
    :param selected_slots: Доменные временные слоты, выбранные клиентом.
        Формат: (day, start_time)
        Пример: (date(2026, 1, 22), time(19, 0))

    :return:
        - FilterAndMatchSlotsUseCase - если у специалиста есть активное правило доступности;
        - None - если правило отсутствует (специалист недоступен)."""

    # 1) Получаем активное правило доступности специалиста
    rule = (
        AvailabilityRule.objects
        .filter(
            creator=psychologist,
            is_active=True,
        )
        .first()
    )

    if rule is None:
        # Без активного правила специалист считается недоступным
        return None

    # 2) Получаем все активные исключения для этого правила
    exceptions = AvailabilityException.objects.filter(
        rule=rule,
        is_active=True,
    )

    # 3) Адаптация Django-моделей → доменные объекты
    domain_rule = map_rule_to_domain(rule)
    domain_exceptions = map_exceptions_to_domain(exceptions)

    # 4) Фильтр доменных слотов по индивидуальным правилам специалиста
    slot_filter = AvailabilitySlotFilter(
        rule=domain_rule,
        exceptions=domain_exceptions,
    )

    # 5) Нормализация timezone специалиста. Это важно для того, чтоб выбранный предпочитаемый слот в TZ клиента
    # корректно вписывался в рабочее расписание (рабочие окна) в TZ специалиста
    rule_tz = rule.timezone

    if isinstance(rule_tz, str):
        psychologist_tz = ZoneInfo(rule_tz)
    elif isinstance(rule_tz, tzinfo):
        psychologist_tz = rule_tz
    else:
        raise TypeError(
            f"Неподдерживаемый тип часового пояса в AvailabilityRule.timezone: {type(rule_tz)!r}"
        )

    normalized_selected_slots: set[SlotKey] = set()

    for dt in selected_slots:
        # dt - timezone-aware datetime (из mapper-а)
        localized_dt = dt.astimezone(psychologist_tz)

        normalized_selected_slots.add(
            (localized_dt.date(), localized_dt.time())
        )

    # 6) Matcher по выбранным пользователем доменным слотам (чистый, без TZ-логики)
    matcher = SelectedSlotsMatcher(
        selected_slots=normalized_selected_slots,
    )

    # 7) Финальная сборка use-case
    return FilterAndMatchSlotsUseCase(
        slot_filter=slot_filter,
        matcher=matcher,
    )
