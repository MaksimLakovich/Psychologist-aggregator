def format_session_duration_minutes(minutes) -> str:
    """Возвращает понятную подпись длительности сессии для клиентских карточек."""
    try:
        normalized_minutes = int(minutes)
    except (TypeError, ValueError):
        normalized_minutes = 0

    if normalized_minutes <= 0:
        return "не указано"

    hours, rest_minutes = divmod(normalized_minutes, 60)

    def hour_label(value):
        if 11 <= value % 100 <= 14:
            hour_word = "часов"
        elif value % 10 == 1:
            hour_word = "час"
        elif value % 10 in (2, 3, 4):
            hour_word = "часа"
        else:
            hour_word = "часов"
        return f"{value} {hour_word}"

    if hours and rest_minutes == 0:
        return hour_label(hours)

    if hours:
        return f"{hours} ч {rest_minutes} мин"

    return f"{normalized_minutes} мин"


def build_session_duration_labels(active_rule):
    """Собирает UI-подписи по активному рабочему правилу специалиста."""
    if not active_rule:
        return {
            "individual": "Индивидуальная сессия · длительность не указана",
            "couple": "Парная сессия · длительность не указана",
        }

    return {
        "individual": f"Индивидуальная сессия · {format_session_duration_minutes(active_rule.session_duration_individual)}",
        "couple": f"Парная сессия · {format_session_duration_minutes(active_rule.session_duration_couple)}",
    }


def get_prefetched_active_rule(profile):
    """Достает активное правило из prefetch-данных профиля без лишних запросов, если оно уже загружено."""
    prefetched_rules = getattr(profile.user, "prefetched_active_availability_rules", None)
    if prefetched_rules is not None:
        return prefetched_rules[0] if prefetched_rules else None

    return profile.user.availability_rules.filter(is_active=True).first()


def attach_session_duration_labels(profile):
    """Добавляет профилю подписи длительности сессий из его активного рабочего расписания."""
    active_rule = get_prefetched_active_rule(profile)
    profile.active_availability_rule = active_rule
    profile.session_duration_labels = build_session_duration_labels(active_rule)
    profile.session_duration_individual_label = profile.session_duration_labels["individual"]
    profile.session_duration_couple_label = profile.session_duration_labels["couple"]
    profile.session_duration_individual_minutes = (
        active_rule.session_duration_individual if active_rule else None
    )
    profile.session_duration_couple_minutes = (
        active_rule.session_duration_couple if active_rule else None
    )
    return profile
