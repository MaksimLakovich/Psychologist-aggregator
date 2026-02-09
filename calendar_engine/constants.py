from datetime import time

from calendar_engine.domain.time_policy.policy import DomainTimePolicy

# ====== ДЛЯ МОДЕЛЕЙ ======
EVENT_TYPE_CHOICES = [
    ("event", "Встреча"),
    ("group_event", "Группа встреч"),
]

EVENT_STATUS_CHOICES = [
    ("draft", "Черновик"),
    ("planned", "Запланировано"),
    ("started", "Начато"),
    ("completed", "Завершено"),
    ("cancelled", "Отменено"),
    ("archived", "Архивировано"),
]

EVENT_VISIBILITY_CHOICES = [
    ("private", "Приватная"),
    ("public", "Публичная"),
]

EVENT_SOURCE_CHOICES = [
    ("internal", "Internal"),
    ("google", "Google Calendar"),
    ("apple", "Apple Calendar"),
    ("outlook", "Outlook"),
]

FREQUENCY_RECURRENCE_CHOICES = [
    ("daily", "Ежедневно"),
    ("weekly", "Еженедельно"),
    ("monthly", "Ежемесячно"),
]

SLOT_STATUS_CHOICES = [
    ("planned", "Запланировано"),
    ("started", "Начато"),
    ("completed", "Завершено"),
    ("cancelled", "Отменено"),
    ("archived", "Архивировано"),
]

PARTICIPANT_EVENT_ROLE_CHOICES = [
    ("organizer", "Организатор"),
    ("participant", "Участник"),
    ("moderator", "Модератор"),
    ("observer", "Наблюдатель"),
]

PARTICIPANT_EVENT_STATUS_CHOICES = [
    ("invited", "Приглашен"),
    ("accepted", "Принято"),
    ("declined", "Отклонено"),
    ("left", "Покинул"),
]

PARTICIPANT_SLOT_ROLE_CHOICES = [
    ("organizer", "Организатор"),
    ("participant", "Участник"),
    ("speaker", "Выступающий"),
    ("moderator", "Модератор"),
    ("observer", "Наблюдатель"),
]

PARTICIPANT_SLOT_STATUS_CHOICES = [
    ("planned", "Запланировано"),
    ("joined", "Присоединился"),
    ("left_early", "Покинул раньше"),
    ("attended", "Посещено"),
    ("missed", "Пропущено"),
]

WEEKDAYS_CHOICES = [
    (0, "Monday"),
    (1, "Tuesday"),
    (2, "Wednesday"),
    (3, "Thursday"),
    (4, "Friday"),
    (5, "Saturday"),
    (6, "Sunday"),
]

AVAILABILITY_EXCEPTION_CHOICES = [
    ("day_off", "Выходной"),
    ("vacation", "Отпуск"),
    ("sick_leave", "Больничный"),
    ("short_day", "Сокращенный день"),
    ("other", "Другое"),
]

EXCEPTION_TYPE_CHOICES = [
    ("unavailable", "Полностью недоступен"),
    ("override", "Частичное переопределение"),
]

# ====== ДЛЯ ДОМЕННОЙ ПОЛИТИКИ ======
DOMAIN_TIME_POLICY = DomainTimePolicy(
    day_time_start=time(0, 0),
    day_time_end=time(0, 0),  # день заканчивается в 00:00 следующего дня
    slot_duration_minutes=60,
)

DAYS_AHEAD_FOR_CLIENT = 7
DAYS_AHEAD_FOR_SPECIALIST = 8
DAYS_AHEAD_FOR_SHOW_SCHEDULE = 9
