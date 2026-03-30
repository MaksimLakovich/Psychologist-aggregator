from django.core.exceptions import ObjectDoesNotExist
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_naive, make_aware

from calendar_engine.booking.exceptions import (
    CreateBookingValidationError, ParseSlotValidationError)
from calendar_engine.models import TimeSlot


def validate_client_can_create_booking(*, client_user) -> None:
    """Проверяет, что клиентское бронирование запускает именно пользователь с client_profile.

    Бизнес-смысл:
        - текущий booking-flow предназначен только для клиентского сценария;
        - специалист и админ получат свои сценарии позже (в системе будут отдельные flow для групповых событий или
          профессиональных событий между специалистами - супервизии, интервизии, семинары и прочее);
        - backend не должен позволять вызвать этот use-case произвольному пользователю без client_profile.
    """
    try:
        client_user.client_profile
    except ObjectDoesNotExist as exc:
        raise CreateBookingValidationError(
            "Создание бронирования доступно только пользователю с ролью клиента."
        ) from exc


def validate_consultation_type_in_therapy_session(*, consultation_type: str) -> None:
    """Проверяет, что формат консультации относится к текущему поддерживаемому scope в рамках therapy_session."""
    if consultation_type not in ("individual", "couple"):
        raise CreateBookingValidationError(
            "consultation_type в терапевтической сессии должен быть либо 'individual', либо 'couple'."
        )


def parse_requested_slot_start(*, slot_start_iso: str):
    """Преобразует ISO-строку старта слота в aware datetime.

    Бизнес-смысл:
        - slot_start_iso приходит из frontend и не должен приниматься без проверки;
        - booking опирается на точный старт доменного слота, поэтому строка обязана корректно парситься;
        - naive datetime недопустим, иначе timezone-логика начнет вести себя непредсказуемо.
    """
    if not slot_start_iso:
        raise ParseSlotValidationError("Не удалось определить выбранный слот для бронирования.")

    parsed_datetime = parse_datetime(slot_start_iso)

    if parsed_datetime is None:
        raise ParseSlotValidationError("Выбранный слот имеет некорректный формат даты и времени.")

    if is_naive(parsed_datetime):
        parsed_datetime = make_aware(parsed_datetime)

    return parsed_datetime


def validate_client_has_no_overlapping_bookings(
    *,
    client_user,
    slot_start_datetime,
    slot_end_datetime,
    ignore_event_ids=None,
) -> None:
    """Проверяет, что у клиента нет другого активного бронирования с пересечением по времени.

    Бизнес-смысл:
        - клиент не может быть одновременно записан сразу на две встречи в один и тот же период;
        - даже если слот свободен у специалиста, backend не должен создавать новое бронирование,
          если у клиента уже существует пересекающаяся встреча;
        - это минимальная защита клиента от двойного бронирования до появления более общей busy-модели.
    """
    overlapping_slots = TimeSlot.objects.filter(
        status__in=["planned", "started"],
        start_datetime__lt=slot_end_datetime,
        end_datetime__gt=slot_start_datetime,
        slot_participants__user=client_user,
    )

    if ignore_event_ids:
        overlapping_slots = overlapping_slots.exclude(event_id__in=ignore_event_ids)

    overlapping_slot_exists = overlapping_slots.distinct().exists()

    if overlapping_slot_exists:
        raise CreateBookingValidationError(
            "Невозможно создать встречу: у клиента уже есть другая сессия в выбранное время."
        )
