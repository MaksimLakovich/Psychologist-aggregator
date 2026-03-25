from dataclasses import dataclass

from django.shortcuts import get_object_or_404
from django.utils import timezone

from calendar_engine.models import CalendarEvent
from core.services.calendar_event_slot_selector import (
    get_event_active_slot, get_event_completed_slot)
from core.services.calendar_slot_time_display import \
    build_calendar_slot_time_display


@dataclass
class TherapySessionDetailData:
    """Общий для клиента и для специалиста контракт данных для detail-страницы терапевтической встречи.

    Бизнес-смысл:
        - и client-версия, и specialist-версия страницы должны опираться на один и тот же источник данных по событию;
        - специфическая role-view потом уже решает, какие блоки и действия показать конкретному пользователю;
        - а этот загрузчик заранее собирает только общую основу:
            - событие;
            - display-slot;
            - второго участника;
            - display-дату/время;
            - базовые флаги и счетчики, которые не должны дублироваться по view.
    """

    event: CalendarEvent
    slot: object | None
    counterpart_participant: object | None
    counterpart_user: object | None
    counterpart_full_name: str
    slot_display_data: dict
    is_finished_slot: bool
    can_open_meeting_url: bool
    slot_participants_count: int
    event_participants_count: int


def _get_event_for_viewer(*, viewer_user, event_id):
    """Возвращает событие detail-screen только если текущий пользователь реально его участник.

    Бизнес-смысл:
        - и клиент, и специалист должны открывать только "свои" встречи;
        - сразу подгружаем те связи, которые потом нужны обеим role-specific страницам:
            - слоты события;
            - участников;
            - профили и справочные данные второй стороны.
    """
    return get_object_or_404(
        CalendarEvent.objects.prefetch_related(
            "slots",
            "slots__slot_participants__user",
            "participants__user__psychologist_profile",
            "participants__user__psychologist_profile__methods",
            "participants__user__psychologist_profile__specialisations",
            "participants__user__psychologist_profile__topics",
        ),
        id=event_id,
        participants__user=viewer_user,
    )


def _get_detail_slot(event):
    """Определяет display-slot для detail-screen встречи.

    Бизнес-смысл:
        - detail-screen должен одинаково корректно открываться и для будущих, и для текущих,
          и для уже завершенных событий;
        - поэтому сначала берем активный слот, потом completed-slot,
          а если статусная модель еще не синхронизировалась, используем fallback по фактическому времени.
    """
    slot = get_event_active_slot(event) or get_event_completed_slot(event)
    if slot is None:
        fallback_completed_slots = [
            event_slot
            for event_slot in event.slots.all()
            if event_slot.end_datetime < timezone.now()
        ]
        slot = next(iter(reversed(fallback_completed_slots)), None)

    return slot


def _get_counterpart_data(*, event, viewer_user):
    """Находит вторую сторону терапевтической встречи относительно текущего пользователя.

    Бизнес-смысл:
        - detail-screen всегда показывается от лица конкретного viewer_user;
        - counterpart = это "другой участник" этой же встречи;
        - дальше client/specialist view уже сами решают, какие данные из counterpart им нужны:
            - профиль специалиста;
            - профиль клиента;
            - имя, фото и дополнительные business-блоки.
    """
    # Для текущего пользователя counterpart = второй участник этой встречи.
    counterpart_participant = next(
        (
            participant
            for participant in event.participants.all()
            if participant.user_id != viewer_user.pk
        ),
        None,
    )
    counterpart_user = counterpart_participant.user if counterpart_participant else None
    counterpart_full_name = (
        f"{counterpart_user.first_name} {counterpart_user.last_name}".strip()
        if counterpart_user
        else ""
    )

    return counterpart_participant, counterpart_user, counterpart_full_name


def load_therapy_session_detail_data(*, viewer_user, event_id, viewer_timezone):
    """Загружает общую detail-основу для терапевтической встречи.

    Бизнес-смысл:
        - role-specific view не должен сам вручную повторять одну и ту же загрузку event/slot/counterpart;
        - shared loader дает единый источник истины для клиентской и будущей specialist-версии страницы;
        - view потом занимается только своей ролью:
            - какие поля можно редактировать;
            - какие блоки показывать в боковой колонке;
            - какие бизнесовые тексты и CTA нужны этой роли.
    """
    event = _get_event_for_viewer(
        viewer_user=viewer_user,
        event_id=event_id,
    )
    slot = _get_detail_slot(event)
    counterpart_participant, counterpart_user, counterpart_full_name = _get_counterpart_data(
        event=event,
        viewer_user=viewer_user,
    )

    # Дату и время всегда готовим по timezone того пользователя, который открыл страницу.
    # Это позволяет обеим ролям видеть встречу в своем актуальном часовом поясе.
    slot_display_data = (
        build_calendar_slot_time_display(
            slot=slot,
            client_timezone=viewer_timezone,
        )
        if slot
        else {}
    )
    # "Встреча закрыта" для detail-экрана определяем не только по статусу, но и по фактическому времени:
    # это позволяет корректно показывать архивную логику даже если статус completed еще не успел обновиться
    is_finished_slot = bool(
        slot
        and (
            slot.status in ["completed", "cancelled"]
            or slot.end_datetime < timezone.now()
        )
    )

    return TherapySessionDetailData(
        event=event,
        slot=slot,
        counterpart_participant=counterpart_participant,
        counterpart_user=counterpart_user,
        counterpart_full_name=counterpart_full_name,
        slot_display_data=slot_display_data,
        is_finished_slot=is_finished_slot,
        can_open_meeting_url=bool(
            slot
            and slot.meeting_url
            and slot.status in ["planned", "started"]
            and slot.end_datetime >= timezone.now()
        ),
        slot_participants_count=len(slot.slot_participants.all()) if slot else 0,
        event_participants_count=len(event.participants.all()),
    )
