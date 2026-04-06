from django.utils import timezone

from calendar_engine.lifecycle.exceptions import LifecycleActionValidationError
from calendar_engine.models import TimeSlot


def validate_slot_can_be_changed(
    *,
    slot: TimeSlot | None,
    action_name: str,
) -> TimeSlot:
    """Проверяет, что со слотом еще можно выполнить действие пользователя.

    Простыми словами:
        - слот должен существовать;
        - слот не должен быть уже завершен;
        - слот не должен быть уже отменен;
        - время встречи не должно уже закончиться.

    Это общий валидатор для lifecycle-действий, которые меняют еще "живую" встречу, например для отмены или переноса.

    Параметр action_name нужен только для понятного текста ошибки:
        - action_name="Отменить"
        - action_name="Перенести"
    """
    if slot is None:
        raise LifecycleActionValidationError("У встречи не найден актуальный слот для выполнения действия")

    if slot.status in ["completed", "cancelled"] or slot.end_datetime <= timezone.now():
        raise LifecycleActionValidationError(
            f"{action_name} можно только действующую встречу"
        )

    return slot
