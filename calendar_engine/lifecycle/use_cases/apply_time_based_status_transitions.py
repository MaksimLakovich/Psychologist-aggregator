from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from calendar_engine.lifecycle.services.event_status_resolver import (
    EventSlotStatusCounts, resolve_calendar_event_status)
from calendar_engine.models import CalendarEvent, TimeSlot


@dataclass(slots=True)
class CalendarStatusTransitionResult:
    """Краткий итог автоматического обновления статусов по времени.

    Нужен, чтобы вызывающий код мог понять:
        - сколько слотов перешло в started;
        - сколько слотов перешло в completed;
        - сколько событий после этого сменили свой статус.

    =====

    1) @dataclass:
        - Python сам создаст __init__();
        - не нужно вручную писать конструктор;
        - объект нужен просто как контейнер для значений.
    2) slots=True:
        - в стандартном режиме Python-объект хранит атрибуты довольно свободно и можно в любой момент
          добавить новое поле, например: obj.test = 123;
        - если указать slots=True, то объект становится более строгим: т.е., можно использовать только заранее
          объявленные поля.
    Это лучше для предотвращения опечаток и меньше расход памяти.
    """

    started_slots_count: int = 0
    completed_slots_count: int = 0
    updated_events_count: int = 0


def _get_target_events_queryset(*, participant_user=None, event_ids=None):
    """Возвращает только те события, которые надо пересчитать в текущем вызове.

    Варианты:
        - все события одного пользователя;
        - одно конкретное событие пользователя;
        - несколько конкретных событий.
    """
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


@transaction.atomic
def apply_time_based_status_transitions(
    *,
    participant_user=None,
    event_ids=None,
    current_datetime=None,
) -> CalendarStatusTransitionResult:
    """Автоматически переводит статусы событий и слотов по текущему времени.

    Что делает use case:
        1) если слот уже начался, переводит его в started;
        2) если слот уже закончился, переводит его в completed;
        3) после этого пересчитывает статус родительского события.

    Параметр current_datetime:
        - обычно не передается, и тогда берется timezone.now();
        - оставлен для тестов, backfill и ситуаций, когда нужен один фиксированный момент времени на всю операцию.
    """
    current_datetime = current_datetime or timezone.now()
    result = CalendarStatusTransitionResult()
    target_events = _get_target_events_queryset(
        participant_user=participant_user,
        event_ids=event_ids,
    )

    # Шаг 1. Ищем слоты, у которых время встречи уже закончилось.
    #     - если "сейчас" уже позже конца встречи, такая встреча больше не может быть ни planned, ни started;
    #     - значит ее нужно перевести в completed.
    #
    # Почему берем и planned, и started:
    #     - planned: если по какой-то причине статус не успел смениться вовремя, но встреча уже закончилась;
    #     - started: это обычный сценарий, когда встреча уже шла и теперь завершилась
    slots_to_complete = TimeSlot.objects.filter(
        event__in=target_events,
        status__in=["planned", "started"],
        end_datetime__lte=current_datetime,
    )

    # Сохраняем, сколько слотов будут переведены в completed в рамках этого запуска.
    # Это нужно для понятного итогового результата функции
    result.completed_slots_count = slots_to_complete.count()
    if result.completed_slots_count:
        # update(...) обновляет все найденные записи одним SQL-запросом.
        # Это быстрее и надежнее, чем менять каждый слот по одному в цикле
        slots_to_complete.update(
            status="completed",
            updated_at=current_datetime,
        )

    # Шаг 2. Ищем слоты, которые уже начались, но еще не закончились
    slots_to_start = TimeSlot.objects.filter(
        event__in=target_events,
        status="planned",
        start_datetime__lte=current_datetime,
        end_datetime__gt=current_datetime,
    )

    # Сохраняем, сколько слотов система перевела в started именно в этом вызове
    result.started_slots_count = slots_to_start.count()
    if result.started_slots_count:
        # Одним SQL-запросом переводим подходящие слоты в started
        slots_to_start.update(
            status="started",
            updated_at=current_datetime,
        )

    # Шаг 3. После обновления самих слотов пересчитываем статус родительских событий.
    #
    # Зачем это нужно:
    #     - пользователь на UI видит не только слот, но и все событие целиком;
    #     - поэтому статус CalendarEvent должен соответствовать тому, что сейчас происходит внутри его слотов.
    #
    # Пример:
    #     - если у события есть хотя бы один started-слот, событие должно быть started;
    #     - если started-слотов нет, но есть будущие planned-слоты, событие должно быть planned;
    #     - если все слоты завершены, событие должно быть completed;
    #     - если все слоты отменены, событие должно быть cancelled
    events_to_update = []

    # annotate(...) просит БД сразу посчитать по каждому событию, сколько у него слотов в каждом статусе:
    #     - started_slots_count = сколько слотов сейчас идет;
    #     - planned_slots_count = сколько еще впереди;
    #     - completed_slots_count = сколько уже завершено;
    #     - cancelled_slots_count = сколько отменено
    recalculated_events = target_events.annotate(
        started_slots_count=Count("slots", filter=Q(slots__status="started"), distinct=True),
        planned_slots_count=Count("slots", filter=Q(slots__status="planned"), distinct=True),
        completed_slots_count=Count("slots", filter=Q(slots__status="completed"), distinct=True),
        cancelled_slots_count=Count("slots", filter=Q(slots__status="cancelled"), distinct=True),
    )

    for event in recalculated_events.iterator():
        # Передаем в resolver числа по слотам и определяем:
        # "Какой статус должно иметь само событие при такой комбинации слотов?"
        #
        # Примеры:
        #     - started=1, planned=0, completed=0, cancelled=0 -> событие started
        #     - started=0, planned=2, completed=1, cancelled=0 -> событие planned
        #     - started=0, planned=0, completed=3, cancelled=0 -> событие completed
        new_status = resolve_calendar_event_status(
            slot_counts=EventSlotStatusCounts(
                started=event.started_slots_count,
                planned=event.planned_slots_count,
                completed=event.completed_slots_count,
                cancelled=event.cancelled_slots_count,
            )
        )
        if new_status and event.status != new_status:
            # В список на сохранение попадают только реально изменившиеся события, чтоб не делать лишние записи в БД
            event.status = new_status
            event.updated_at = current_datetime
            events_to_update.append(event)

    if events_to_update:
        # bulk_update(...) массово сохраняет все измененные события одним запросом
        CalendarEvent.objects.bulk_update(
            events_to_update,
            ["status", "updated_at"],
            batch_size=200,
        )

        # Возвращаем инфо, сколько событий действительно получили новый статус
        result.updated_events_count = len(events_to_update)

    return result


# thin-wrapper: тонкая обертка над общей функцией
def apply_time_based_status_transitions_for_user(
    *,
    participant_user,
    current_datetime=None,
) -> CalendarStatusTransitionResult:
    """Пересчитывает по времени все события одного пользователя."""
    return apply_time_based_status_transitions(
        participant_user=participant_user,
        current_datetime=current_datetime,
    )


# thin-wrapper: тонкая обертка над общей функцией
def apply_time_based_status_transitions_for_event(
    *,
    participant_user,
    event_id,
    current_datetime=None,
) -> CalendarStatusTransitionResult:
    """Пересчитывает по времени только одно выбранное событие пользователя."""
    return apply_time_based_status_transitions(
        participant_user=participant_user,
        event_ids=[event_id],
        current_datetime=current_datetime,
    )
