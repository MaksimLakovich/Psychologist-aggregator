from django.db import transaction
from calendar_engine.lifecycle.exceptions import LifecycleActionValidationError
from calendar_engine.lifecycle.services.slot_action_validator import \
    validate_slot_can_be_changed
from calendar_engine.lifecycle.services.event_status_resolver import \
    recalculate_calendar_event_status
from calendar_engine.models import TimeSlot


@transaction.atomic
def cancel_event_slot(*, slot: TimeSlot | None, cancel_reason: str) -> TimeSlot:
    """Отменяет текущий слот события по инициативе пользователя.

    Бизнес-смысл:
        - пользователь отменяет еще не завершенную встречу;
        - текущий слот получает статус cancelled;
        - в слот записывается причина отмены;
        - затем пересчитывается статус всего CalendarEvent с учетом остальных слотов.

    Пример:
        - если у события это был единственный слот, событие тоже станет cancelled;
        - если у события есть другие будущие planned-слоты, событие останется planned.
    """
    slot = validate_slot_can_be_changed(slot=slot, action_name="Отменить")  # Проверяет, что слот еще можно менять
    cancel_reason = (cancel_reason or "").strip()

    if not cancel_reason:
        raise LifecycleActionValidationError("Для отмены встречи нужно указать причину")

    # 1) Отменяется текущая встреча (слот)
    slot.status = "cancelled"
    slot.cancel_reason_type = "cancelled_by_user"
    slot.cancel_reason = cancel_reason
    slot.full_clean()
    slot.save(update_fields=["status", "cancel_reason_type", "cancel_reason", "updated_at"])

    # 2) Пересчитывается статус всего CalendarEvent с учетом остальных слотов
    recalculate_calendar_event_status(event=slot.event)

    return slot
