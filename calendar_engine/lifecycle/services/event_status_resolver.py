from dataclasses import dataclass

from django.db.models import Count, Q

from calendar_engine.models import CalendarEvent


@dataclass(slots=True)
class EventSlotStatusCounts:
    """Счетчики статусов всех слотов внутри одного события.

    Пояснение:
        - у одного CalendarEvent может быть несколько TimeSlot (мульти-событие);
        - чтобы понять, какой статус должен быть у самого события - считаем, сколько у него слотов в каждом статусе.

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

    started: int = 0
    planned: int = 0
    completed: int = 0
    cancelled: int = 0


def _build_event_slot_status_counts(*, event: CalendarEvent) -> EventSlotStatusCounts:
    """Считает, сколько слотов события сейчас находятся в каждом статусе.

    Пример:
        - started = 1 слот;
        - planned = 2 слота;
        - completed = 0 слотов;
        - cancelled = 0 слотов.

    Такой набор потом нужен, чтобы уже одним правилом решить, какой статус должен быть у самого CalendarEvent.
    """
    slot_counts = event.slots.aggregate(
        started_slots_count=Count("id", filter=Q(status="started")),
        planned_slots_count=Count("id", filter=Q(status="planned")),
        completed_slots_count=Count("id", filter=Q(status="completed")),
        cancelled_slots_count=Count("id", filter=Q(status="cancelled")),
    )

    return EventSlotStatusCounts(
        started=slot_counts["started_slots_count"],
        planned=slot_counts["planned_slots_count"],
        completed=slot_counts["completed_slots_count"],
        cancelled=slot_counts["cancelled_slots_count"],
    )


def resolve_calendar_event_status(*, slot_counts: EventSlotStatusCounts) -> str | None:
    """Определяет, какой статус должен быть у самого события по его слотам.

    Правило приоритета:
        - если хотя бы один слот уже started, событие тоже started;
        - если started нет, но есть planned, событие planned;
        - если started/planned нет, но есть completed, событие completed;
        - если остались только cancelled, событие cancelled.

    Нужно, чтобы статус CalendarEvent всегда честно отражал текущее состояние его TimeSlot, а не жил отдельно от них.
    """
    if slot_counts.started > 0:
        return "started"

    if slot_counts.planned > 0:
        return "planned"

    if slot_counts.completed > 0:
        return "completed"

    if slot_counts.cancelled > 0:
        return "cancelled"

    return None


def recalculate_calendar_event_status(*, event: CalendarEvent) -> CalendarEvent:
    """Пересчитывает и при необходимости обновляет статус события.

    Простыми словами:
        - берем все слоты события;
        - смотрим, какие у них статусы сейчас;
        - по этим слотам решаем, какой статус должен быть у CalendarEvent;
        - если он изменился, сохраняем новое значение в БД.
    """
    slot_counts = _build_event_slot_status_counts(event=event)
    new_status = resolve_calendar_event_status(slot_counts=slot_counts)

    if new_status and event.status != new_status:
        event.status = new_status
        event.save(update_fields=["status", "updated_at"])

    return event
