from django.contrib import admin

from calendar_engine.models import (AvailabilityException,
                                    AvailabilityExceptionTimeWindow,
                                    AvailabilityRule,
                                    AvailabilityRuleTimeWindow, CalendarEvent,
                                    EventParticipant, RecurrenceRule,
                                    SlotParticipant, TimeSlot)

# =====
# СОБЫТИЕ / СЛОТЫ
# =====


def build_participant_display(*, participant) -> str:
    """Собирает краткое описание участника для колонок админки.

    Бизнес-смысл:
        - когда администратор открывает список событий или слотов, ему важно сразу видеть
          не только факт наличия участника, но и кто это именно, а также какова его роль
          и текущий статус в событии/слоте;
        - это позволяет быстро понять состав встречи без открытия каждой записи отдельно.
    """
    user = participant.user
    full_name = f"{user.first_name} {user.last_name}".strip()
    display_name = full_name or user.email
    role_display = participant.get_role_display()
    status_display = participant.get_status_display()
    return f"{display_name} ({role_display}, {status_display})"


class CreatorAndReadonlyFields(admin.ModelAdmin):
    """Базовый класс для админок, чтоб не дублировать в них повторяющийся код
    (например, параметры для readonly_fields или функцию сохранения creator при создании объекта."""

    readonly_fields = ("creator", "created_at", "updated_at")  # чтобы в админке их случайно не изменили

    def save_model(self, request, obj, form, change):
        """Автоматическое сохранение creator в создаваемом объекте."""
        if not obj.creator_id:
            obj.creator = request.user
        super().save_model(request, obj, form, change)


@admin.register(CalendarEvent)
class CalendarEventAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели CalendarEvent в админке."""

    list_display = (
        "id",
        "creator",
        "title",
        "event_type",
        "status",
        "event_participants_display",
        "cancel_reason_type",
        "visibility",
        "is_recurring",
        "source",
    )
    list_filter = ("event_type", "status", "cancel_reason_type", "visibility", "is_recurring", "source")
    search_fields = ("title", "description", "creator__email", "creator__last_name")
    ordering = ("creator__email", "-created_at")
    list_display_links = ("id", "title")  # чтобы кликать на название вместо ID

    def get_queryset(self, request):
        """Подгружаем участников события заранее, чтобы колонка списка не делала N+1 запросов."""
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("participants__user")

    @admin.display(description="Участники")
    def event_participants_display(self, obj):
        """Показывает состав участников события прямо в списке админки.

        Бизнес-смысл:
            - администратору важно сразу видеть, кто участвует во встрече;
            - дополнительно рядом показываем роль и статус, чтобы было понятно,
              кто организатор, кто приглашен и кто уже подтвердил участие.
        """
        participants = [build_participant_display(participant=participant) for participant in obj.participants.all()]
        return ", ".join(participants) if participants else "Нет участников"


@admin.register(RecurrenceRule)
class RecurrenceRuleAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели RecurrenceRule в админке."""

    list_display = ("id", "creator", "event", "rule_start", "rule_end", "count_recurrences", "frequency", "is_active")
    list_filter = ("is_active", "frequency")
    search_fields = ("event__title", "creator__email", "creator__last_name")
    ordering = ("creator__email", "-created_at")


@admin.register(TimeSlot)
class TimeSlotAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели TimeSlot в админке."""

    list_display = (
        "id",
        "creator",
        "event",
        "slot_participants_display",
        "start_datetime",
        "end_datetime",
        "status",
        "slot_index",
    )
    list_filter = ("status",)
    search_fields = ("event__title", "creator__email", "creator__last_name")
    ordering = ("creator__email", "-created_at")

    def get_queryset(self, request):
        """Подгружаем участников слота заранее, чтобы колонка списка не делала N+1 запросов."""
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("slot_participants__user")

    @admin.display(description="Участники")
    def slot_participants_display(self, obj):
        """Показывает состав участников слота прямо в списке админки.

        Бизнес-смысл:
            - даже если событие составное и состоит из нескольких слотов, администратор
              должен быстро видеть состав конкретного временного интервала;
            - это особенно важно, если в будущем у разных слотов одного события
              состав участников может отличаться.
        """
        participants = [build_participant_display(participant=participant) for participant in obj.slot_participants.all()]
        return ", ".join(participants) if participants else "Нет участников"


@admin.register(EventParticipant)
class EventParticipantAdmin(admin.ModelAdmin):
    """Настройка отображения модели EventParticipant в админке."""

    list_display = ("id", "event", "user", "joined_at", "left_at", "role", "status")
    list_filter = ("role", "status")
    search_fields = ("event__title", "user__email", "user__last_name")
    ordering = ("user__email", "-created_at")
    readonly_fields = ("created_at", "updated_at")  # чтобы в админке их случайно не изменили
    raw_id_fields = ("event", "user")


@admin.register(SlotParticipant)
class SlotParticipantAdmin(admin.ModelAdmin):
    """Настройка отображения модели SlotParticipant в админке."""

    list_display = ("id", "slot", "user", "joined_at", "left_at", "role", "status")
    list_filter = ("role", "status")
    search_fields = ("user__email", "user__last_name")
    ordering = ("user__email", "-created_at")
    readonly_fields = ("created_at", "updated_at")  # чтобы в админке их случайно не изменили
    raw_id_fields = ("slot", "user",)


# =====
# РАБОЧИЙ ГРАФИК
# =====


@admin.register(AvailabilityRuleTimeWindow)
class AvailabilityRuleTimeWindowAdmin(admin.ModelAdmin):
    """Настройка отображения модели AvailabilityRuleTimeWindow в админке."""

    list_display = ("id", "rule", "start_time", "end_time", "rule__is_active")
    list_filter = ("rule__is_active",)
    search_fields = ("rule__creator__email", "rule__creator__last_name")
    ordering = ("rule", "start_time", "-created_at")


class RuleTimeWindowInline(admin.TabularInline):
    """Канонический способ для того чтоб потом в админке AvailabilityRuleAdmin вывести данные из связанной модели
    о временных окнах данного правила:
     - просмотр временных окон;
     - редактирование/создание новых временных окон в правиле."""
    model = AvailabilityRuleTimeWindow
    extra = 0
    min_num = 1
    fields = ("start_time", "end_time")


@admin.register(AvailabilityRule)
class AvailabilityRuleAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели AvailabilityRule в админке."""

    list_display = (
        "id",
        "creator",
        "rule_start",
        "rule_end",
        "weekdays",
        "session_duration_individual",
        "session_duration_couple",
        "break_between_sessions",
        "minimum_booking_notice_hours",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("creator__email", "creator__last_name")
    ordering = ("creator__email", "-created_at")
    inlines = (RuleTimeWindowInline,)


@admin.register(AvailabilityExceptionTimeWindow)
class AvailabilityExceptionTimeWindowAdmin(admin.ModelAdmin):
    """Настройка отображения модели AvailabilityExceptionTimeWindow в админке."""

    list_display = ("id", "exception", "override_start_time", "override_end_time", "exception__is_active")
    list_filter = ("exception__is_active",)
    search_fields = ("exception__creator__email", "exception__creator__last_name")
    ordering = ("exception", "override_start_time", "-created_at")


class ExceptionTimeWindowInline(admin.TabularInline):
    """Канонический способ для того чтоб потом в админке AvailabilityExceptionAdmin вывести данные из связанной модели
    о временных окнах данного исключения:
     - просмотр временных окон;
     - редактирование/создание новых временных окон в исключении."""
    model = AvailabilityExceptionTimeWindow
    extra = 0
    min_num = 1
    fields = ("override_start_time", "override_end_time")


@admin.register(AvailabilityException)
class AvailabilityExceptionAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели AvailabilityException в админке."""

    list_display = (
        "id",
        "creator",
        "rule",
        "exception_start",
        "exception_end",
        "reason",
        "exception_type",
        "override_session_duration_individual",
        "override_session_duration_couple",
        "override_break_between_sessions",
        "override_minimum_booking_notice_hours",
        "is_active",
    )
    list_filter = ("is_active", "reason", "exception_type")
    search_fields = ("rule__creator__email", "creator__email", "creator__last_name")
    ordering = ("creator__email", "-created_at")
    inlines = (ExceptionTimeWindowInline,)
