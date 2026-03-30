from django.db import transaction
from calendar_engine.booking.use_cases.therapy_session_create import \
    CreateTherapySessionUseCase
from calendar_engine.booking.validators import parse_requested_slot_start
from calendar_engine.lifecycle.exceptions import LifecycleActionValidationError
from calendar_engine.lifecycle.services.event_status_resolver import \
    recalculate_calendar_event_status
from calendar_engine.lifecycle.services.slot_action_validator import \
    validate_slot_can_be_changed
from calendar_engine.models import TimeSlot


@transaction.atomic
def reschedule_therapy_session_slot(
    *,
    slot: TimeSlot | None,
    client_user,
    specialist_profile_id: int,
    slot_start_iso: str,
    consultation_type: str,
) -> dict:
    """Переносит встречу на новый слот.

    Что происходит:
        - сначала создается новое событие на выбранный слот;
        - в новом событии сохраняется ссылка на старое через previous_event;
        - старый слот помечается как cancelled с причиной rescheduled;
        - затем пересчитывается статус старого события.
    """
    slot = validate_slot_can_be_changed(slot=slot, action_name="Перенести")  # Проверяет, что слот еще можно менять
    requested_slot_start_datetime = parse_requested_slot_start(slot_start_iso=slot_start_iso)  # Преобразует ISO-строку

    if requested_slot_start_datetime == slot.start_datetime:
        raise LifecycleActionValidationError("Новый слот должен отличаться от текущего времени встречи")

    # 1) Создаем новую встречу (слот)
    create_use_case = CreateTherapySessionUseCase()
    booking_result = create_use_case.execute(
        client_user=client_user,
        specialist_profile_id=specialist_profile_id,
        slot_start_iso=slot_start_iso,
        consultation_type=consultation_type,
        previous_event=slot.event,
        previous_event_id=slot.event_id,
    )

    # 2) Отменяется текущая встреча (слот)
    slot.status = "cancelled"
    slot.cancel_reason_type = "rescheduled"
    slot.cancel_reason = "Встреча перенесена на другой временной слот"
    slot.full_clean()
    slot.save(update_fields=["status", "cancel_reason_type", "cancel_reason", "updated_at"])

    # 3) Пересчитывается статус всего CalendarEvent с учетом остальных слотов
    recalculate_calendar_event_status(event=slot.event)

    return booking_result
