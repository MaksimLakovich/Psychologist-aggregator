from calendar_engine.models import CalendarEvent


def get_latest_rescheduled_descendant(
    *,
    event: CalendarEvent | None,
    viewer_user=None,
) -> CalendarEvent | None:
    """Возвращает актуального потомка события по цепочке previous_event.

    Бизнес-смысл:
        - после нескольких переносов пользователь из старой встречи должен попадать в текущую встречу той же цепочки;
        - прямой child не всегда достаточен, потому что его могли потом перенести еще раз;
        - если из-за старых данных у события неожиданно несколько direct-children, берем самый ранний child,
          потому что именно он с наибольшей вероятностью является каноническим следующим звеном цепочки.
    """
    if event is None:
        return None

    current_event = event
    visited_ids = {current_event.id}

    while True:
        next_events = CalendarEvent.objects.filter(previous_event_id=current_event.id)

        if viewer_user is not None:
            next_events = next_events.filter(participants__user=viewer_user)

        next_event = next_events.order_by("created_at", "id").distinct().first()
        if next_event is None or next_event.id in visited_ids:
            return None if current_event == event else current_event

        visited_ids.add(next_event.id)
        current_event = next_event
