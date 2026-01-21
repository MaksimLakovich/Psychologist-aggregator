from django.contrib import admin

from calendar_engine.models import (AvailabilityException, AvailabilityRule,
                                    CalendarEvent, EventParticipant,
                                    RecurrenceRule, SlotParticipant, TimeSlot)


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

    list_display = ("id", "creator", "title", "event_type", "status", "visibility", "is_recurring", "source")
    list_filter = ("event_type", "status", "visibility", "is_recurring", "source")
    search_fields = ("title", "description", "creator__email", "creator__last_name")
    ordering = ("creator__email", "-created_at")
    list_display_links = ("id", "title")  # чтобы кликать на название вместо ID


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

    list_display = ("id", "creator", "event", "start_datetime", "end_datetime", "status", "slot_index")
    list_filter = ("status",)
    search_fields = ("event__title", "creator__email", "creator__last_name")
    ordering = ("creator__email", "-created_at")


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


@admin.register(AvailabilityRule)
class AvailabilityRuleAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели AvailabilityRule в админке."""

    list_display = (
        "id", "creator", "rule_start", "rule_end", "weekdays", "slot_duration_minutes", "break_minutes", "is_active"
    )
    list_filter = ("is_active",)
    search_fields = ("creator__email", "creator__last_name")
    ordering = ("creator__email", "-created_at")


@admin.register(AvailabilityException)
class AvailabilityExceptionAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели AvailabilityException в админке."""

    list_display = (
        "id",
        "creator",
        "rule",
        "exception_date_start",
        "exception_date_end",
        "exception_start_time",
        "exception_end_time",
        "reason",
        "exception_type",
        "is_active",
    )
    list_filter = ("is_active", "reason", "exception_type")
    search_fields = ("rule__creator__email", "creator__email", "creator__last_name")
    ordering = ("creator__email", "-created_at")
