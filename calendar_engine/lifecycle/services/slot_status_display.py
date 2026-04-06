from calendar_engine.models import TimeSlot


def build_calendar_slot_status_display(*, slot: TimeSlot | None) -> str:
    """Возвращает пользовательский display-статус слота/события для UI.

    Бизнес-смысл:
        - lifecycle-слой знает и фиксирует различие между обычной отменой и отменой из-за переноса;
        - технически слот после переноса остается cancelled, но в интерфейсе клиент должен видеть "Перенесено";
        - helper нужен как единый источник истины для detail-страницы и списка встреч.
    """
    if slot is None:
        return ""

    if slot.status == "cancelled" and slot.cancel_reason_type == "rescheduled":
        return "Перенесено"

    return slot.get_status_display() or "Запланировано"
