EVENT_TYPE_CHOICES = [
    ("event", "Встреча"),
    ("group_event", "Группа встреч"),
],

EVENT_STATUS_CHOICES = [
    ("draft", "Черновик"),
    ("planned", "Запланировано"),
    ("started", "Начато"),
    ("completed", "Завершено"),
    ("canceled", "Отменено"),
    ("archived", "Архивировано"),
],

EVENT_VISIBILITY_CHOICES = [
    ("private", "Приватная"),
    ("public", "Публичная"),
],

EVENT_SOURCE_CHOICES = [
    ("internal", "Internal"),
    ("google", "Google Calendar"),
    ("apple", "Apple Calendar"),
    ("outlook", "Outlook"),
],

FREQUENCY_RECURRENCE_CHOICES = [
    ("daily", "Ежедневно"),
    ("weekly", "Еженедельно"),
    ("monthly", "Ежегодно"),
],

SLOT_STATUS_CHOICES = [
    ("planned", "Запланировано"),
    ("started", "Начато"),
    ("completed", "Завершено"),
    ("canceled", "Отменено"),
    ("archived", "Архивировано"),
    ("no_show", "Неявка"),
    ("blocked", "Заблокирован"),
],

PARTICIPANT_EVENT_ROLE_CHOICES = [
    ("organizer", "Организатор"),
    ("participant", "Участник"),
    ("observer", "Наблюдатель"),
],

PARTICIPANT_EVENT_STATUS_CHOICES = [
    ("invited", "Приглашен"),
    ("accepted", "Принято"),
    ("declined", "Отклонено"),
    ("removed", "Покинул"),
],

PARTICIPANT_SLOT_ROLE_CHOICES = [
    ("organizer", "Организатор"),
    ("participant", "Участник"),
],

PARTICIPANT_SLOT_STATUS_CHOICES = [
    ("planned", "Запланировано"),
    ("joined", "Присоединился"),
    ("left_early", "Покинул раньше"),
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

GLOBAL_AVAILABILITY_TYPE_CHOICES = [
    ("available", "Доступный"),
    ("unavailable", "Недоступный")
],
