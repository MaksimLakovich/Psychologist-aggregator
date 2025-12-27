EVENT_TYPE_CHOICES = [
    ("event", "Встреча"),
    ("group_event", "Группа встреч"),
],

EVENT_STATUS_CHOICES = [
    ("draft", "Черновик"),
    ("planned", "Запланировано"),
    ("current", "Текущее"),
    ("rescheduled", "Перенесено"),
    ("completed", "Завершено"),
    ("cancelled", "Отменено"),
],

EVENT_SOURCE_CHOICES = [
    ("internal", "Internal"),
    ("google", "Google Calendar"),
    ("apple", "Apple Calendar"),
    ("outlook", "Outlook"),
],

SLOT_STATUS_CHOICES = [
    ("planned", "Запланировано"),
    ("current", "Текущее"),
    ("rescheduled", "Перенесено"),
    ("completed", "Завершено"),
    ("cancelled", "Отменено"),
],

PARTICIPANT_ROLE_CHOICES = [
    ("organizer", "Организатор"),
    ("participant", "Участник"),
    ("observer", "Наблюдатель"),
],

PARTICIPANT_EVENT_STATUS_CHOICES = [
    ("invited", "Приглашен"),
    ("accepted", "Принято"),
    ("declined", "Отклонено"),
    ("removed", "Удалено"),
],

PARTICIPANT_SLOT_STATUS_CHOICES = [
    ("planned", "Запланировано"),
    ("attended", "Посещено"),
    ("missed", "Пропущено"),
],