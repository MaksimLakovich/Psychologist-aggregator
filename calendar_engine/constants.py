EVENT_TYPE_CHOICES = [
    ("event", "Встреча"),
    ("group_event", "Группа встреч"),
],

EVENT_STATUS_CHOICES = [
    ("draft", "Черновик"),
    ("planned", "Запланировано"),
    ("started", "Начато"),
    ("rescheduled", "Перенесено"),
    ("completed", "Завершено"),
    ("canceled", "Отменено"),
],

EVENT_SOURCE_CHOICES = [
    ("internal", "Internal"),
    ("google", "Google Calendar"),
    ("apple", "Apple Calendar"),
    ("outlook", "Outlook"),
],

SLOT_STATUS_CHOICES = [
    ("planned", "Запланировано"),
    ("started", "Начато"),
    ("rescheduled", "Перенесено"),
    ("completed", "Завершено"),
    ("canceled", "Отменено"),
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

WEEKDAYS_CHOICES = [
    (0, "Monday"),
    (1, "Tuesday"),
    (2, "Wednesday"),
    (3, "Thursday"),
    (4, "Friday"),
    (5, "Saturday"),
    (6, "Sunday"),
],

AVAILABILITY_EXCEPTION_CHOICES = [
    ("day_off", "Выходной"),
    ("vacation", "Отпуск"),
    ("sick_leave", "Больничный"),
],
