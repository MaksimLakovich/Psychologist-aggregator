from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from calendar_engine.models import CalendarEvent, TimeSlot


@dataclass(slots=True)
class CalendarStatusTransitionResult:
    """Итог применения автоматических time-based переходов статусов."""

    started_slots_count: int = 0
    completed_slots_count: int = 0
    updated_events_count: int = 0


def _get_target_events_queryset(*, participant_user=None, event_ids=None):
    """Возвращает события, для которых можно безопасно применить time-based lifecycle-переходы."""
    queryset = CalendarEvent.objects.filter(
        status__in=["planned", "started", "completed"],
    )

    if participant_user is not None:
        queryset = queryset.filter(participants__user=participant_user)

    if event_ids is not None:
        if not event_ids:
            return queryset.none()
        queryset = queryset.filter(id__in=event_ids)

    return queryset.distinct()


def _resolve_event_status(
        *, started_slots_count: int, planned_slots_count: int, completed_slots_count: int
) -> str | None:
    """Определяет итоговый статус CalendarEvent по текущему набору статусов его слотов."""
    if started_slots_count > 0:
        return "started"

    if planned_slots_count > 0:
        return "planned"

    if completed_slots_count > 0:
        return "completed"

    return None


@transaction.atomic
def apply_time_based_status_transitions(
    *,
    participant_user=None,
    event_ids=None,
    current_datetime=None,
) -> CalendarStatusTransitionResult:
    """Применяет автоматические переходы статусов событий и слотов по фактическому времени."""
    current_datetime = current_datetime or timezone.now()
    result = CalendarStatusTransitionResult()
    target_events = _get_target_events_queryset(
        participant_user=participant_user,
        event_ids=event_ids,
    )

    slots_to_complete = TimeSlot.objects.filter(
        event__in=target_events,
        status__in=["planned", "started"],
        end_datetime__lte=current_datetime,
    )
    result.completed_slots_count = slots_to_complete.count()
    if result.completed_slots_count:
        slots_to_complete.update(
            status="completed",
            updated_at=current_datetime,
        )

    slots_to_start = TimeSlot.objects.filter(
        event__in=target_events,
        status="planned",
        start_datetime__lte=current_datetime,
        end_datetime__gt=current_datetime,
    )
    result.started_slots_count = slots_to_start.count()
    if result.started_slots_count:
        slots_to_start.update(
            status="started",
            updated_at=current_datetime,
        )

    events_to_update = []
    recalculated_events = target_events.annotate(
        started_slots_count=Count("slots", filter=Q(slots__status="started"), distinct=True),
        planned_slots_count=Count("slots", filter=Q(slots__status="planned"), distinct=True),
        completed_slots_count=Count("slots", filter=Q(slots__status="completed"), distinct=True),
    )

    for event in recalculated_events.iterator():
        new_status = _resolve_event_status(
            started_slots_count=event.started_slots_count,
            planned_slots_count=event.planned_slots_count,
            completed_slots_count=event.completed_slots_count,
        )
        if new_status and event.status != new_status:
            event.status = new_status
            event.updated_at = current_datetime
            events_to_update.append(event)

    if events_to_update:
        CalendarEvent.objects.bulk_update(
            events_to_update,
            ["status", "updated_at"],
            batch_size=200,
        )
        result.updated_events_count = len(events_to_update)

    return result
