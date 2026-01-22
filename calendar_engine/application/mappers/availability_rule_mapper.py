from calendar_engine.domain.availability.user_rules import \
    WeeklyAvailabilityRule


def map_availability_rule_to_domain(rule) -> WeeklyAvailabilityRule:
    """Адаптирует django-объект AvailabilityRule в доменное правило доступности.
    Без этой адаптации получаем ошибку."""

    weekdays = set(rule.weekdays)

    # Пока у нас устанавливается одно окно в день (start_time + end_time), но в будущем легко расширяется
    # до нескольких окон (например, работает с 8 до 12 и с 18 до 22)
    time_windows = [
        (rule.start_time, rule.end_time),
    ]

    return WeeklyAvailabilityRule(
        weekdays=weekdays,
        time_windows=time_windows,
    )
