import uuid
from datetime import time

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from timezone_field import TimeZoneField

from calendar_engine.services import get_local_date_for_user
from calendar_engine.constants import (AVAILABILITY_EXCEPTION_CHOICES,
                                       EVENT_CANCEL_REASON_TYPE_CHOICES,
                                       EVENT_SOURCE_CHOICES,
                                       EVENT_STATUS_CHOICES,
                                       EVENT_TYPE_CHOICES,
                                       EVENT_VISIBILITY_CHOICES,
                                       EXCEPTION_TYPE_CHOICES,
                                       FREQUENCY_RECURRENCE_CHOICES,
                                       PARTICIPANT_EVENT_ROLE_CHOICES,
                                       PARTICIPANT_EVENT_STATUS_CHOICES,
                                       PARTICIPANT_SLOT_ROLE_CHOICES,
                                       PARTICIPANT_SLOT_STATUS_CHOICES,
                                       SLOT_STATUS_CHOICES, WEEKDAYS_CHOICES)

# =====
# СОБЫТИЕ / СЛОТЫ
# =====


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
    creator = models.ForeignKey(
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
        default="session_individual",
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
    visibility = models.CharField(
        choices=EVENT_VISIBILITY_CHOICES,
        default="private",
        max_length=32,
        null=False,
        blank=False,
        verbose_name="Видимость события",
        help_text="Укажите видимость события",
    )
    capacity = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Максимально допустимое количество участников в групповом событии",
        help_text="Укажите максимально допустимое количество участников в групповом событии"
    )
    is_recurring = models.BooleanField(
        default=False,
        null=False,
        blank=False,
        verbose_name="Повторяющееся события",
        help_text="Флаг повторяющегося события",
    )
    previous_event = models.ForeignKey(
        to="self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rescheduled_events",
        verbose_name="Предыдущее событие при переносе",
        help_text="Связь с предыдущим событием при переносе",
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
        return f"{self.id} - {self.title}"

    def clean(self):
        """Модельная валидация бизнес-инвариантов события.

        Дополнительно:
            - previous_event хранится в НОВОМ событии после переноса, а не в старом отмененном;
            - событие не может ссылаться само на себя как на previous_event.
        """
        super().clean()

        errors = {}

        if self.previous_event_id:
            if self.pk and self.previous_event_id == self.pk:
                errors["previous_event"] = "Событие не может ссылаться само на себя как на previous_event"

            if self.status == "cancelled":
                errors["previous_event"] = (
                    "previous_event нужно хранить в новом событии после переноса, а не в старом отмененном событии"
                )

        if errors:
            raise ValidationError(errors)

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"
        ordering = ["-created_at"]


class RecurrenceRule(TimeStampedModel):
    """Правила для повторяющегося события."""

    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="recurrences_rules",
        verbose_name="Пользователь",
        help_text="Укажите пользователя",
    )
    event = models.ForeignKey(
        to=CalendarEvent,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="recurrences",
        verbose_name="Событие для повторения",
        help_text="Укажите событие для повторения",
    )
    timezone = TimeZoneField(
        blank=True,
        null=True,
        verbose_name="Часовой пояс",
        help_text="Для корректного применения правила повторения в календаре пользователя",
    )
    rule_start = models.DateField(
        null=False,
        blank=False,
        verbose_name="Дата старта правила повторения",
        help_text="Укажите дату старта правила повторения",
    )
    rule_end = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата окончания правила повторения",
        help_text="Укажите дату окончания правила повторения",
    )
    count_recurrences = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Максимальное количество повторений",
        help_text="Укажите максимальное количество повторений",
    )
    frequency = models.CharField(
        choices=FREQUENCY_RECURRENCE_CHOICES,
        max_length=32,
        null=True,
        blank=True,
        verbose_name="Периодичность повторения",
        help_text="Укажите периодичность повторения (monthly / weekly / daily)",
    )
    interval = models.PositiveSmallIntegerField(
        default=1,
        null=False,
        blank=False,
        verbose_name="Интервал повторения",
        help_text="Интервал повторения (1 - каждую неделю, 2 - через неделю)",
    )
    weekdays_recurrences = ArrayField(
        models.PositiveSmallIntegerField(choices=WEEKDAYS_CHOICES),
        null=True,
        blank=True,
        verbose_name="Дни недели для повторений",
        help_text="Укажите дни недели для повторения",
    )
    is_active = models.BooleanField(
        default=True,
        null=False,
        blank=False,
        verbose_name="Признак действия правила повторения",
        help_text="Флаг действия правила повторения",
    )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.creator} / ({self.rule_start} - {self.rule_end})"

    class Meta:
        verbose_name = "Правило повторения события"
        verbose_name_plural = "Правила повторений событий"
        ordering = ["pk", "creator", "rule_start"]


class TimeSlot(TimeStampedModel):
    """Атом времени внутри события календаря (конкретный интервал времени, часть события)."""

    # Это как primary_key вместо системного автоинкремента id, чтоб было более безопасно для публичных API
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="owned_slots",
        verbose_name="Владелец слота",
        help_text="Укажите владельца слота",
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
    meeting_resume = models.TextField(
        null=True,
        blank=True,
        verbose_name="Итоги встречи",
        help_text="Укажите краткий протокол, выводы или результаты проведенной встречи",
    )
    cancel_reason_type = models.CharField(
        choices=EVENT_CANCEL_REASON_TYPE_CHOICES,
        max_length=32,
        null=True,
        blank=True,
        verbose_name="Тип причины отмены слота",
        help_text="Укажите тип причины отмены конкретной встречи внутри события",
    )
    cancel_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="Причина отмены слота",
        help_text="Укажите текстовое пояснение причины отмены конкретной встречи",
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
        return f"{self.id} - {self.event.title}"

    def clean(self):
        """Модельная валидация бизнес-инвариантов конкретной встречи внутри события.

        Бизнес-смысл:
            - для multi-slot события отмена должна относиться к конкретному TimeSlot, а не ко всему CalendarEvent;
            - meeting_resume можно хранить только у реально завершенной встречи;
            - cancel_reason_type и cancel_reason должны заполняться только у отмененного слота.
        """
        super().clean()

        errors = {}

        if self.status == "cancelled":
            if not self.cancel_reason_type:
                errors["cancel_reason_type"] = (
                    "Для отмененного слота обязательно нужно указать тип причины отмены"
                )

            if not self.cancel_reason:
                errors["cancel_reason"] = (
                    "Для отмененного слота обязательно нужно указать текстовое пояснение причины отмены"
                )
        else:
            if self.cancel_reason_type:
                errors["cancel_reason_type"] = (
                    "Тип причины отмены можно указывать только для слота со статусом cancelled"
                )

            if self.cancel_reason:
                errors["cancel_reason"] = (
                    "Текстовую причину отмены можно указывать только для слота со статусом cancelled"
                )

        if self.status != "completed" and self.meeting_resume:
            errors["meeting_resume"] = (
                "Итоги встречи можно сохранять только для слота со статусом completed"
            )

        if errors:
            raise ValidationError(errors)

    class Meta:
        verbose_name = "Слот"
        verbose_name_plural = "Слоты"
        unique_together = ("event", "slot_index")
        ordering = ["start_datetime", "event", "slot_index"]
        indexes = [
            models.Index(fields=["start_datetime", "end_datetime"]),
        ]
        # Защита от double booking (защита от пересечений слотов одного creator):
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_datetime__gt=models.F("start_datetime")),
                name="slot_end_after_start",
            ),
            ExclusionConstraint(
                name="prevent_slot_overlap_per_creator",
                expressions=[
                    (models.F("creator"), "="),
                    (
                        models.Func(
                            models.F("start_datetime"),
                            models.F("end_datetime"),
                            function="tstzrange",
                        ),
                        "&&",
                    ),
                ],
                # Предотвращать наложение только для активных слотов (запланированных/начатых).
                # Исторические слоты не должны блокировать доступность.
                condition=models.Q(status__in=["planned", "started"]),
            ),
        ]
        # ВАЖНО: для корректной работы constraint нужно включить расширение btree_gist.
        # ExclusionConstraint НЕ РАБОТАЕТ, если в PostgreSQL не включено расширение:
        #   CREATE EXTENSION IF NOT EXISTS btree_gist;
        #
        # Чтобы правильно это сделать в Django нужно:
        #   1) Создаем миграцию вручную (один раз): python manage.py makemigrations calendar_engine
        #   2) Добавляем в нее операцию перед созданием constraint:
        #       from django.contrib.postgres.operations import BtreeGistExtension
        #
        #       class Migration(migrations.Migration):
        #
        #           operations = [
        #               BtreeGistExtension(),
        #               ...
        #           ]
        # Без этого PostgreSQL либо упадет, либо constraint просто не создастся.


class TimeSlotMessage(TimeStampedModel):
    """Сообщение участников внутри конкретноого события.

    Бизнес-смысл:
        - одно текстовое поле message у TimeSlot не позволяет построить нормальное обсуждение;
        - отдельная модель дает форум/чат внутри встречи:
            - несколько сообщений;
            - разные авторы;
            - редактирование своих сообщений;
            - история по created_at / updated_at.
    """

    # Это как primary_key вместо системного автоинкремента id, чтоб было более безопасно для публичных API
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="authored_slot_messages",
        verbose_name="Автор сообщения",
        help_text="Укажите пользователя, который оставил сообщение внутри встречи",
    )
    slot = models.ForeignKey(
        to=TimeSlot,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="messages",
        verbose_name="Слот встречи",
        help_text="Укажите встречу, к которой относится сообщение",
    )
    message = models.TextField(
        null=False,
        blank=False,
        verbose_name="Текст сообщения",
        help_text="Укажите текст сообщения участника встречи",
    )
    is_rewrited = models.BooleanField(
        default=False,
        null=False,
        blank=False,
        verbose_name="Сообщение отредактировано",
        help_text="Флаг нужен, чтобы на UI показывать, что автор уже менял текст сообщения",
    )

    def __str__(self):
        """Краткое строковое представление сообщения для админки и shell."""
        return f"{self.creator} -> {self.slot_id}"

    def clean(self):
        """Модельная валидация сообщения внутри встречи.

        Бизнес-смысл:
            - сообщения должны оставлять только реальные участники конкретной встречи;
            - пустые или состоящие из пробелов тексты для форумного сценария не имеют смысла.
        """
        super().clean()

        errors = {}

        if self.message is not None and not self.message.strip():
            errors["message"] = "Сообщение не может состоять только из пробелов"

        if self.creator_id and self.slot_id:
            is_participant = self.slot.event.participants.filter(user_id=self.creator_id).exists()
            if not is_participant:
                errors["creator"] = (
                    "Оставлять сообщения внутри встречи могут только участники этого события"
                )

        if errors:
            raise ValidationError(errors)

    class Meta:
        verbose_name = "Сообщение встречи"
        verbose_name_plural = "Сообщения встреч"
        ordering = ["-created_at"]


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
    joined_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата/время присоединения",
    )
    left_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата/время выхода",
    )
    role = models.CharField(
        choices=PARTICIPANT_EVENT_ROLE_CHOICES,
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
        return f"{self.pk} - {self.event.title} - {self.user.email}"

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
        related_name="slot_participations",
        verbose_name="Участник слота события",
        help_text="Укажите участника слота события",
    )
    joined_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата/время присоединения",
    )
    left_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата/время выхода",
    )
    role = models.CharField(
        choices=PARTICIPANT_SLOT_ROLE_CHOICES,
        default="participant",
        max_length=32,
        null=False,
        blank=False,
        verbose_name="Роль участника в слоте",
        help_text="Укажите роль участника в слоте событии",
    )
    status = models.CharField(
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
        return f"{self.pk} - {self.slot.id} - {self.user.email}"

    class Meta:
        verbose_name = "Участник слота в событии"
        verbose_name_plural = "Участники слота в событии"
        unique_together = ("slot", "user")
        ordering = ["pk", "slot__start_datetime", "slot", "user"]


# =====
# РАБОЧИЙ ГРАФИК
# =====


class AvailabilityRule(TimeStampedModel):
    """Правила доступности специалиста (рабочее расписание).

    Например: Пн-Пт, с набором рабочих окон внутри дня:
        - одно окно с 09:00 до 18:00;
        - или несколько окон с 06:00 до 11:00 и с 16:00 до 22:00.
    """

    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="availability_rules",
        verbose_name="Пользователь",
        help_text="Укажите пользователя",
    )
    timezone = TimeZoneField(
        blank=True,
        null=True,
        verbose_name="Часовой пояс",
        help_text="Для корректного применения правила в календаре пользователя",
    )
    rule_start = models.DateField(
        null=False,
        blank=False,
        verbose_name="Дата начала действия правила",
        help_text="Укажите дату начала действия правила",
    )
    rule_end = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата окончания действия правила",
        help_text="Укажите дату окончания действия правила",
    )
    weekdays = ArrayField(
        models.PositiveSmallIntegerField(choices=WEEKDAYS_CHOICES),
        null=False,
        blank=False,
        verbose_name="Рабочие дни недели",
        help_text="Укажите рабочие дни недели",
    )
    session_duration_individual = models.PositiveSmallIntegerField(
        default=50,
        null=False,
        blank=False,
        verbose_name="Продолжительность 1 индивидуальной сессии (минуты)",
        help_text="Укажите продолжительность 1 индивидуальной сессии (минуты)",
    )
    session_duration_couple = models.PositiveSmallIntegerField(
        default=90,
        null=False,
        blank=False,
        verbose_name="Продолжительность 1 парной сессии (минуты)",
        help_text="Укажите продолжительность 1 парной сессии (минуты)",
    )
    break_between_sessions = models.PositiveSmallIntegerField(
        default=10,
        null=True,
        blank=True,
        verbose_name="Перерыв между сессиями (минуты)",
        help_text="Укажите перерыв между сессиями (минуты)",
    )
    minimum_booking_notice_hours = models.PositiveSmallIntegerField(
        default=1,
        null=False,
        blank=False,
        verbose_name="Минимальное количество часов до ближайшего доступного слота для записи",
        help_text="Укажите, за сколько минимум часов до начала слота клиенту можно показывать слот для записи",
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
        return f"{self.creator} / {self.weekdays}"

    def clean(self):
        """Модельная валидация периода действия рабочего расписания.

        Бизнес-смысл:
            - новое активное правило нельзя создавать задним числом;
            - дата окончания не может быть раньше даты начала;
            - если срок действия уже истек, правило должно быть закрытым (is_active=False), а не активным.
        """
        super().clean()

        errors = {}

        # Возвращает текущую дату в часовом поясе пользователя
        today = get_local_date_for_user(self.creator if self.creator_id else None)

        if self.rule_start and self.rule_end and self.rule_start > self.rule_end:
            errors["rule_end"] = "Дата окончания рабочего расписания не может быть раньше даты его начала."

        # Пояснение по "_state.adding":
        # 1) у каждого объекта модели Django есть служебное поле _state;
        # 2) внутри него Django хранит техническую информацию о состоянии объекта;
        # 3) self._state.adding == True означает, что это новый объект, он еще не сохранен в базе;
        # 4) self._state.adding == False означает, что этот объект уже существует в базе, сейчас его редактируют.
        # Т.е., это можно понимать так:
        #   - self.is_active отвечает за бизнес-смысл: активно правило или нет;
        #   - self._state.adding отвечает за технический смысл: создаем новый объект или обновляем уже существующий

        # Пояснение: текущая логика с "self._state.adding and self.is_active" означает более узкое правило:
        # - запрещаем даты в прошлом только в момент создания нового активного правила;
        # - но не валим ошибкой старое уже существующее активное правило, если его открыли на редактирование позже,
        # когда его rule_start уже стал "в прошлом", но пользователь в этом правиле решил например изменить
        # продолжительность сессии или перерыв.
        # Именно поэтому self._state.adding здесь отделяет "создание нового правила" от "редактирования существующего"
        if self._state.adding and self.is_active:
            if self.rule_start and self.rule_start < today:
                errors["rule_start"] = "Дата начала рабочего расписания не может быть в прошлом."

            if self.rule_end and self.rule_end < today:
                errors["rule_end"] = "Дата окончания рабочего расписания не может быть в прошлом."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Сохраняет правило и закрывает его активные исключения, если само правило стало закрытым."""
        was_active = None

        # Если объект уже есть в БД, то достаем из БД его старое значение is_active и кладем в was_active:
        # 1) "type(self).objects" это почти то же самое, что "AvailabilityRule.objects". Потому что этот код
        # находится внутри метода модели, то type(self) позволяет обратиться к менеджеру именно текущего класса;
        # 2) Пояснение по values_list():
        # - это Django QuerySet-метод, который возвращает не объекты модели целиком, а только выбранные поля.
        # - если написать БЕЗ "flat=True", то результат будет например такой: [(True,)]
        # - а если написать ".values_list("is_active", flat=True)", то результат будет уже: [True]
        # - по сути "flat=True" убирает лишнюю обертку tuple и возвращает плоский список значений
        if self.pk:
            was_active = (
                type(self).objects
                .filter(pk=self.pk)
                .values_list("is_active", flat=True)
                .first()
            )

        # Если дата окончания уже прошла, правило автоматически должно уйти в архив "is_active=False"
        today = get_local_date_for_user(self.creator if self.creator_id else None)
        if self.rule_end and self.rule_end < today:
            self.is_active = False
            update_fields = kwargs.get("update_fields")
            # Так как у нас произошло изменения is_active, то необходимо автоматическое обязательное
            # добавление "is_active" к любому набору, который будет передаваться в kwargs["update_fields"]
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"is_active"}

        super().save(*args, **kwargs)

        # Закрытое правило не должно оставлять после себя активные исключения, поэтому нужно закрыть и их.
        # Пояснение:
        # - availabilityexception_set это автоматическая обратная связь от ForeignKey по аналогии с related_name;
        # - если у ForeignKey не указан related_name, а у нас в AvailabilityException.rule он не указан сейчас, то
        #   Django сам придумывает имя для доступа "назад" по умолчанию: имя_модели_в_нижнем_регистре + "_set"
        if self.is_active is False and was_active is not False:
            self.availabilityexception_set.filter(is_active=True).update(is_active=False)

    def deactivate(self):
        """Метод для деактивации рабочего правила и закрытия связанных активных исключений."""
        self.is_active = False
        self.save(update_fields=["is_active"])

    @classmethod
    def deactivate_active_for_user(cls, user):
        """Закрывает все активные правила пользователя и их действующие исключения.

        Пояснение:
        1) По бизнес-логике у пользователя должно быть максимум одно активное правило;
        2) Но мы делаем защитный код - т.е., исходим не из идеального мира, а из реального где в базе иногда
           могут появиться кривые данные из-за: старой версии кода; ручных правок в админке; миграции; бага и т.д.
        """
        active_rule_ids = list(
            cls.objects
            .filter(creator=user, is_active=True)
            .values_list("pk", flat=True)
        )

        if not active_rule_ids:
            return 0

        AvailabilityException.objects.filter(
            rule_id__in=active_rule_ids,
            is_active=True,
        ).update(is_active=False)

        return cls.objects.filter(pk__in=active_rule_ids).update(is_active=False)

    @classmethod
    def close_expired_for_user(cls, user):
        """Автоматически архивирует правила пользователя, у которых уже прошла дата окончания.

        Пояснение:
        1) По бизнес-логике у пользователя должно быть максимум одно активное правило;
        2) Но мы делаем защитный код - т.е., исходим не из идеального мира, а из реального где в базе иногда
           могут появиться кривые данные из-за: старой версии кода; ручных правок в админке; миграции; бага и т.д.
        """
        today = get_local_date_for_user(user)
        expired_rule_ids = list(
            cls.objects
            .filter(creator=user, is_active=True, rule_end__lt=today)
            .values_list("pk", flat=True)
        )

        if not expired_rule_ids:
            return 0

        AvailabilityException.objects.filter(
            rule_id__in=expired_rule_ids,
            is_active=True,
        ).update(is_active=False)

        return cls.objects.filter(pk__in=expired_rule_ids).update(is_active=False)

    class Meta:
        verbose_name = "Правило доступности"
        verbose_name_plural = "Правила доступности"
        ordering = ["pk", "creator", "rule_start"]


class AvailabilityRuleTimeWindow(TimeStampedModel):
    """Временное окно доступности внутри рабочего дня из AvailabilityRule
    (например, "с 09:00 до 18:00")."""

    rule = models.ForeignKey(
        to=AvailabilityRule,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="time_windows",
        verbose_name="Рабочее расписание",
        help_text="Укажите рабочее расписание",
    )
    start_time = models.TimeField(
        null=False,
        blank=False,
        verbose_name="Начало временного окна",
        help_text="Укажите начало временного окна",
    )
    end_time = models.TimeField(
        null=False,
        blank=False,
        verbose_name="Окончание временного окна",
        help_text="Укажите окончание временного окна",
    )

    def clean(self):
        """Метод валидации для двух сценариев:
            1) 'start_time = end_time': круглосуточный рабочий график;
            2) 'start_time > end_time': проверка, что время начала не может быть раньше, чем время окончания.
        """
        if self.start_time == self.end_time and self.start_time != time(0, 0):
            raise ValidationError(
                "start_time и end_time могут совпадать только для 24/7 (00:00–00:00)"
            )

        # 00:00 в окончании окна считаем концом текущих суток, поэтому например "09:00-00:00" допустимо
        elif self.start_time > self.end_time and self.end_time != time(0, 0):
            raise ValidationError(
                "start_time должен быть меньше end_time"
            )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.rule} (временное окно: с {self.start_time} до {self.end_time})"

    class Meta:
        verbose_name = "Временное окно доступности"
        verbose_name_plural = "Временные окна доступности"
        ordering = ["rule", "start_time"]


class AvailabilityException(TimeStampedModel):
    """Исключения из правил доступности специалиста (отпуск, болезнь, day-off)."""

    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="availability_exceptions",
        verbose_name="Пользователь",
        help_text="Укажите пользователя",
    )
    rule = models.ForeignKey(
        to=AvailabilityRule,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Правило для которого устанавливается исключение",
        help_text="Укажите правило для которого устанавливается исключение",
    )
    exception_start = models.DateField(
        null=False,
        blank=False,
        verbose_name="Дата начала действия исключения",
        help_text="Укажите дату начала действия исключения",
    )
    exception_end = models.DateField(
        null=False,
        blank=False,
        verbose_name="Дата окончания действия исключения",
        help_text="Укажите дату окончания действия исключения",
    )
    reason = models.CharField(
        choices=AVAILABILITY_EXCEPTION_CHOICES,
        max_length=32,
        null=False,
        blank=False,
        verbose_name="Причина исключения",
        help_text="Укажите причину исключения",
    )
    exception_type = models.CharField(
        choices=EXCEPTION_TYPE_CHOICES,
        default="unavailable",
        null=False,
        blank=False,
        verbose_name="Тип исключения",
        help_text="Укажите тип исключения (полностью недоступен или изменение текущего рабочего правила",
    )
    override_session_duration_individual = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Продолжительность 1 индивидуальной сессии согласно исключения (минуты)",
        help_text="Укажите продолжительность 1 индивидуальной сессии согласно исключения (минуты)",
    )
    override_session_duration_couple = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Продолжительность 1 парной сессии согласно исключения (минуты)",
        help_text="Укажите продолжительность 1 парной сессии согласно исключения (минуты)",
    )
    override_break_between_sessions = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Перерыв между сессиями согласно исключения (минуты)",
        help_text="Укажите перерыв между сессиями согласно исключения (минуты)",
    )
    override_minimum_booking_notice_hours = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Новое минимальное количество часов до ближайшего доступного слота для записи",
        help_text="Укажите новое минимальное количество часов до старта слота для записи на период исключения",
    )
    is_active = models.BooleanField(
        default=True,
        null=False,
        blank=False,
        verbose_name="Признак действия исключения",
        help_text="Флаг действия исключения",
    )

    def clean(self):
        """Модельная валидация исключения из рабочего расписания.

        Бизнес-смысл нового параметра такой:
            - базовое правило специалиста задает общий minimum_booking_notice_hours;
            - exception_type="override" может временно переопределить duration / break / minimum notice;
            - exception_type="unavailable" полностью закрывает дату/диапазон дат, поэтому отдельный minimum notice
              и прочие override-настройки для него не нужны и только запутают смысл данных.
        """
        super().clean()

        errors = {}

        # Возвращает текущую дату в часовом поясе пользователя
        today = get_local_date_for_user(self.creator if self.creator_id else None)

        if self.exception_start and self.exception_end and self.exception_end < self.exception_start:
            errors["exception_end"] = "Дата окончания исключения не может быть раньше даты начала исключения."

        # Пояснение по "_state.adding":
        # 1) у каждого объекта модели Django есть служебное поле _state;
        # 2) внутри него Django хранит техническую информацию о состоянии объекта;
        # 3) self._state.adding == True означает, что это новый объект, он еще не сохранен в базе;
        # 4) self._state.adding == False означает, что этот объект уже существует в базе, сейчас его редактируют.
        # Т.е., это можно понимать так:
        #   - self.is_active отвечает за бизнес-смысл: активно правило или нет;
        #   - self._state.adding отвечает за технический смысл: создаем новый объект или обновляем уже существующий
        if self._state.adding and self.is_active:
            if self.exception_start and self.exception_start < today:
                errors["exception_start"] = "Дата начала исключения не может быть в прошлом."

            if self.exception_end and self.exception_end < today:
                errors["exception_end"] = "Дата окончания исключения не может быть в прошлом."

        if self.exception_type == "unavailable":
            if self.override_session_duration_individual is not None:
                errors["override_session_duration_individual"] = (
                    "Для exception_type='unavailable' нельзя указывать override_session_duration_individual, "
                    "потому что день и так полностью закрыт."
                )

            if self.override_session_duration_couple is not None:
                errors["override_session_duration_couple"] = (
                    "Для exception_type='unavailable' нельзя указывать override_session_duration_couple, "
                    "потому что день и так полностью закрыт."
                )

            if self.override_break_between_sessions is not None:
                errors["override_break_between_sessions"] = (
                    "Для exception_type='unavailable' нельзя указывать override_break_between_sessions, "
                    "потому что день и так полностью закрыт."
                )

            if self.override_minimum_booking_notice_hours is not None:
                errors["override_minimum_booking_notice_hours"] = (
                    "Для exception_type='unavailable' нельзя указывать override_minimum_booking_notice_hours, "
                    "потому что день и так полностью закрыт."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.creator} / {self.exception_start}–{self.exception_end} ({self.exception_type})"

    def save(self, *args, **kwargs):
        """Сохраняет исключение и закрывает его, если дата окончания уже прошла."""
        today = get_local_date_for_user(self.creator if self.creator_id else None)
        if self.exception_end and self.exception_end < today:
            self.is_active = False
            update_fields = kwargs.get("update_fields")
            # Так как у нас произошло изменения is_active, то необходимо автоматическое обязательное
            # добавление "is_active" к любому набору, который будет передаваться в kwargs["update_fields"]
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"is_active"}

        super().save(*args, **kwargs)

    @classmethod
    def close_expired_for_user(cls, user):
        """Автоматически архивирует исключения, которые больше не могут действовать.

        Сюда попадают:
            - исключения с прошедшей датой окончания;
            - исключения от уже закрытого рабочего правила;
            - исключения без рабочего правила.
        """
        today = get_local_date_for_user(user)
        # Q - это специальный Django-объект для сложных условий запроса.
        # 1) Он нужен, когда необходимо задать условия: "ИЛИ" / "НЕ" / "сложную комбинацию условий".
        # 2) Без Q обычный .filter(...) внутри одного вызова сработает как простой оператор "И".
        return (
            cls.objects
            .filter(creator=user, is_active=True)
            .filter(
                Q(exception_end__lt=today)  # lt = меньше чем, а символ "|" означает "ИЛИ"
                | Q(rule__is_active=False)  # смотрим поле is_active у связанного объекта rule
                | Q(rule__isnull=True)
            )
            .update(is_active=False)
        )

    class Meta:
        verbose_name = "Исключение из правил доступности"
        verbose_name_plural = "Исключения из правил доступности"
        ordering = ["pk", "creator", "exception_start"]


class AvailabilityExceptionTimeWindow(TimeStampedModel):
    """Переопределенное временное окно доступности внутри рабочего дня из AvailabilityException
    (например, "с 09:00 до 18:00")."""

    exception = models.ForeignKey(
        to=AvailabilityException,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="time_windows",
        verbose_name="Исключение",
        help_text="Укажите исключение",
    )
    # Если exception_type=override (переопределение), то:
    override_start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Новое начало временного окна согласно исключения",
        help_text="Укажите новое начало временного окна согласно исключения",
    )
    override_end_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Новое окончание временного окна согласно исключения",
        help_text="Укажите новое окончание временного окна согласно исключения",
    )

    def clean(self):
        """Метод валидации для двух сценариев:
            1) 'override_start_time = override_end_time': круглосуточный рабочий график;
            2) 'override_start_time > override_end_time': проверка, что время начала не может быть раньше,
                чем время окончания.
        """
        if self.override_start_time and self.override_end_time:

            if (self.override_start_time == self.override_end_time
                    and self.override_start_time != time(0, 0)):
                raise ValidationError(
                    "override_start_time и override_end_time могут совпадать только для 24/7 (00:00-00:00)"
                )

            # 00:00 в окончании окна считаем концом текущих суток, поэтому например "09:00-00:00" допустимо
            elif (self.override_start_time > self.override_end_time
                  and self.override_end_time != time(0, 0)):
                raise ValidationError("override_start_time должен быть меньше override_end_time")

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.exception} (временное окно: с {self.override_start_time} до {self.override_end_time})"

    class Meta:
        verbose_name = "Переопределенное временное окно доступности"
        verbose_name_plural = "Переопределенные временные окна доступности"
        ordering = ["exception", "override_start_time"]
