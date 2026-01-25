from datetime import date, time
from typing import Iterable, Optional

from calendar_engine.application.mappers.exception_mapper import \
    map_exceptions_to_domain
from calendar_engine.application.mappers.rule_mapper import map_rule_to_domain
from calendar_engine.application.use_cases.filter_and_match_availability import \
    FilterAndMatchSlotsUseCase
from calendar_engine.domain.availability.get_user_slots import \
    AvailabilitySlotFilter
from calendar_engine.domain.matching.matcher import SelectedSlotsMatcher
from calendar_engine.models import AvailabilityException, AvailabilityRule

# Тип ключа выбранного пользователем доменного слота:
# (day, start_time)
SlotKey = tuple[date, time]


def build_generate_and_match_use_case(
    *,
    psychologist,
    selected_slots: Iterable[SlotKey],
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

    # 5) Matcher по выбранным пользователем доменным слотам
    matcher = SelectedSlotsMatcher(
        selected_slots=selected_slots,
    )

    # 6) Финальная сборка use-case
    return FilterAndMatchSlotsUseCase(
        slot_filter=slot_filter,
        matcher=matcher,
    )
