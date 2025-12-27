import uuid
from django.conf import settings
from django.db import models
from calendar_engine.constants import (EVENT_TYPE_CHOICES, EVENT_STATUS_CHOICES, EVENT_SOURCE_CHOICES,
                                       SLOT_STATUS_CHOICES, PARTICIPANT_ROLE_CHOICES, PARTICIPANT_EVENT_STATUS_CHOICES,
                                       PARTICIPANT_SLOT_STATUS_CHOICES, WEEKDAYS_CHOICES,
                                       AVAILABILITY_EXCEPTION_CHOICES)
from timezone_field import TimeZoneField


class TimeStampedModel(models.Model):
    """Абстрактная базовая модель для дальнейшего создания *created_at* и *updated_at*
    во всех моделях приложения при необходимости."""

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )

    class Meta:
        """Обязательный параметр для абстрактных базовых моделей."""
        abstract = True


class CalendarEvent(TimeStampedModel):
    """Корень агрегата - событие календаря. Может содержать 1 или несколько временных слотов."""

    # Это как primary_key вместо системного автоинкремента id, чтоб было более безопасно для публичных API
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organizer = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="organized_events",
        verbose_name="Организатор",
        help_text="Укажите пользователя, организатора события",
    )
    title = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Название события",
        help_text="Укажите название события",
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="Описание события",
        help_text="Укажите описание события",
    )
    event_type = models.CharField(
        choices=EVENT_TYPE_CHOICES,
        default="event",
        max_length=32,
        null=False,
        blank=False,
        verbose_name="Тип события",
        help_text="Укажите тип события",
    )
    status = models.CharField(
        choices=EVENT_STATUS_CHOICES,
        default="draft",
        max_length=32,
        null=False,
        blank=False,
        verbose_name="Статус события",
        help_text="Укажите статус события",
    )
    is_recurring = models.BooleanField(
        null=False,
        blank=False,
        verbose_name="Повторяющееся события",
        help_text="Флаг повторяющегося события",
    )
    source = models.CharField(
        choices=EVENT_SOURCE_CHOICES,
        default="internal",
        max_length=32,
        null=False,
        blank=False,
        verbose_name="Источник события",
        help_text="Укажите источник события",
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ID события во внешнем календаре",
        help_text="Укажите ID события во внешнем календаре"
    )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.id - self.title}"

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"
        ordering = ["id"]


class TimeSlot(TimeStampedModel):
    """Атом времени внутри события календаря (конкретный интервал времени, часть события)."""

    # Это как primary_key вместо системного автоинкремента id, чтоб было более безопасно для публичных API
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    event = models.ForeignKey(
        to=CalendarEvent,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="slots",
        verbose_name="Слот для события",
        help_text="Укажите слот для события",
    )
    start_datetime = models.DateTimeField(
        null=False,
        blank=False,
        verbose_name="Начало события",
        help_text="Укажите начало события",
    )
    end_datetime = models.DateTimeField(
        null=False,
        blank=False,
        verbose_name="Окончание события",
        help_text="Укажите окончание события",
    )
    status = models.CharField(
        choices=SLOT_STATUS_CHOICES,
        default="planned",
        max_length=32,
        null=False,
        blank=False,
        verbose_name="Статус слота",
        help_text="Укажите статус слота",
    )
    # Установка "poetry add django-timezone-field"
    # + импорт "from timezone_field import TimeZoneField" + INSTALLED_APPS
    timezone = TimeZoneField(
        blank=True,
        null=True,
        verbose_name="Часовой пояс",
        help_text="Для корректного отображения слотов в календаре пользователя",
    )
    meeting_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="Ссылка на видео-комнату",
        help_text="Укажите ссылку на видео-комнату",
    )
    comment = models.TextField(
        null=True,
        blank=True,
        verbose_name="Комментарий",
        help_text="Укажите комментарий",
    )
    slot_index = models.PositiveSmallIntegerField(
        default=1,
        null=False,
        blank=False,
        verbose_name="Порядок слота внутри события",
        help_text="Укажите порядок слота внутри события"
    )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.id - self.event.title}"

    class Meta:
        verbose_name = "Слот"
        verbose_name_plural = "Слоты"
        ordering = ["id", "slot_index"]
        indexes = [
            models.Index(fields=["start_datetime", "end_datetime"]),
        ]


class EventParticipant(TimeStampedModel):
    """Участник события с ролью и статусом."""

    event = models.ForeignKey(
        to=CalendarEvent,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="participants",
        verbose_name="Событие",
        help_text="Укажите событие",
    )
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="calendar_participations",
        verbose_name="Участник события",
        help_text="Укажите участника события",
    )
    role = models.CharField(
        choices=PARTICIPANT_ROLE_CHOICES,
        default="participant",
        max_length=32,
        null=False,
        blank=False,
        verbose_name="Роль участника в событии",
        help_text="Укажите роль участника в событии",
    )
    status = models.CharField(
        choices=PARTICIPANT_EVENT_STATUS_CHOICES,
        default="invited",
        max_length=32,
        null=False,
        blank=False,
        verbose_name="Статус участника в событии",
        help_text="Укажите статус участника в событии",
    )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.pk - self.event.title - self.user.email}"

    class Meta:
        verbose_name = "Участник события"
        verbose_name_plural = "Участники события"
        unique_together = ("event", "user")
        ordering = ["pk", "event", "user"]


class SlotParticipant(TimeStampedModel):
    """Связь участника с конкретным слотом. Используется, если участники различаются по слотам.
    Редкая, но важная модель для организации составных событий с разным составом участников."""

    slot = models.ForeignKey(
        to=TimeSlot,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="slot_participants",
        verbose_name="Слот события",
        help_text="Укажите слот события",
    )
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="calendar_participations",
        verbose_name="Участник слота события",
        help_text="Укажите участника слота события",
    )
    attendance_status = models.CharField(
        choices=PARTICIPANT_SLOT_STATUS_CHOICES,
        default="planned",
        max_length=32,
        null=False,
        blank=False,
        verbose_name="Статус участника в слоте события",
        help_text="Укажите статус участника в слоте события",
    )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.pk - self.slot.id - self.user.email}"

    class Meta:
        verbose_name = "Участник слота в событии"
        verbose_name_plural = "Участники слота в событии"
        unique_together = ("slot", "user")
        ordering = ["pk", "slot", "user"]


class AvailabilityRule(TimeStampedModel):
    """Правила доступности специалиста (рабочее расписание).
    Например: Пн-Пт, 10:00–18:00."""

    owner = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="availability_rules",
        verbose_name="Пользователь",
        help_text="Укажите пользователя",
    )
    rule_start = models.DateField(
        null=False,
        blank=False,
        verbose_name="Дата старта правила",
        help_text="Укажите дату старта правила",
    )
    rule_end = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата окончания правила",
        help_text="Укажите дату окончания правила",
    )
    weekdays = models.PositiveSmallIntegerField(
        choices=WEEKDAYS_CHOICES,
        null=False,
        blank=False,
        verbose_name="Рабочие дни недели",
        help_text="Укажите рабочие дни недели",
    )
    start_time = models.TimeField(
        null=False,
        blank=False,
        verbose_name="Начало рабочего дня",
        help_text="Укажите начало рабочего дня",
    )
    end_time = models.TimeField(
        null=False,
        blank=False,
        verbose_name="Окончание рабочего дня",
        help_text="Укажите окончание рабочего дня",
    )
    slot_duration_minutes = models.PositiveSmallIntegerField(
        default=60,
        null=False,
        blank=False,
        verbose_name="Продолжительность 1 слота",
        help_text="Укажите продолжительность 1 слота",
    )
    break_minutes = models.PositiveSmallIntegerField(
        default=0,
        null=True,
        blank=True,
        verbose_name="Перерыв между сессиями",
        help_text="Укажите перерыв между сессиями",
    )
    is_active = models.BooleanField(
        default=True,
        null=False,
        blank=False,
        verbose_name="Признак действия правила",
        help_text="Флаг действия правила",
    )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.owner (self.start_time - self.end_time / self.weekdays)}"

    class Meta:
        verbose_name = "Правило доступности специалиста"
        verbose_name_plural = "Правила доступности специалиста"
        ordering = ["pk", "owner", "rule_start"]


class AvailabilityException(models.Model):
    """Исключения из правил доступности специалиста (отпуск, болезнь, day-off)."""

    owner = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="availability_exceptions",
        verbose_name="Пользователь",
        help_text="Укажите пользователя",
    )
    exception_start = models.DateField(
        null=False,
        blank=False,
        verbose_name="Дата старта исключения",
        help_text="Укажите дату старта исключения",
    )
    exception_end = models.DateField(
        null=False,
        blank=False,
        verbose_name="Дата окончания исключения",
        help_text="Укажите дату окончания исключения",
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Время начала исключения",
        help_text="Укажите время начала исключения",
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Время окончания исключения",
        help_text="Укажите время окончания исключения",
    )
    reason = models.CharField(
        choices = AVAILABILITY_EXCEPTION_CHOICES,
        max_length = 32,
        null = True,
        blank = True,
        verbose_name = "Причина исключения",
        help_text = "Укажите причину исключения",
    )
    is_available = models.BooleanField(
        default=True,
        null=True,
        blank=True,
        verbose_name="Признак глобальной доступности специалиста (True - доступен / False - недоступен)",
        help_text="False - полностью недоступен"
    )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.owner} - {self.exception_start} ({'Доступен' if self.is_available else 'Недоступен'})"

    class Meta:
        verbose_name = "Исключение из правил доступности"
        verbose_name_plural = "Исключения из правил доступности"
        ordering = ["pk", "owner", "exception_start"]
