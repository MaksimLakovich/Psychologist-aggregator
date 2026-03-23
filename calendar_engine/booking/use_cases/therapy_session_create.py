from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from calendar_engine.application.factories.generate_specialist_schedule_factory import \
    build_specialist_schedule_runtime_context
from calendar_engine.application.use_cases.specialist_schedule import \
    GenerateSpecialistScheduleUseCase
from calendar_engine.booking.exceptions import \
    CreateTherapySessionValidationError
from calendar_engine.booking.services import (
    get_specialist_profile_for_booking_therapy_session,
    normalize_user_timezone)
from calendar_engine.booking.validators import (
    parse_requested_slot_start, validate_client_can_create_therapy_session,
    validate_client_has_no_overlapping_therapy_sessions,
    validate_consultation_type_in_therapy_session)
from calendar_engine.models import (CalendarEvent, EventParticipant,
                                    SlotParticipant, TimeSlot)


class CreateTherapySessionUseCase:
    """Прикладной сценарий для клиента по созданию встречи (терапевтическая сессия) со специалистом.

    Текущий use-case:
        - клиент выбирает специалиста;
        - клиент выбирает доступный доменный слот в расписании специалиста;
        - backend повторно проверяет, что этот старт (слот или слоты, если время сессии > 1 часа) еще реально доступен;
        - создаются CalendarEvent / TimeSlot / EventParticipant / SlotParticipant.

    Важно:
        - доменная сетка стартов (слотов) остается общим правилом домена для всех участников;
        - индивидуальные значения в рабочем расписании специалиста (session_duration_* и break_between_sessions)
          НЕ меняют доменную сетку, а накладываются на нее;
        - индивидуальные значения в рабочем расписании специалиста используются только для проверки
          доступности старта (слота/слотов) и для расчета чистого TimeSlot.end_datetime.
    """

    @staticmethod
    def _build_specialist_slot_start_datetime(*, slot, specialist_timezone) -> datetime:
        """Преобразует SlotDTO в aware datetime старта в timezone специалиста."""
        return datetime.combine(slot.day, slot.start, tzinfo=specialist_timezone)

    def _find_matching_available_slot(self, *, requested_slot_start_datetime, specialist_timezone, available_slots):
        """Ищет среди актуального расписания ровно тот доменный старт (слот), который выбрал клиент."""
        requested_start_in_specialist_tz = requested_slot_start_datetime.astimezone(specialist_timezone)

        for slot in available_slots:
            slot_start_datetime = self._build_specialist_slot_start_datetime(
                slot=slot,
                specialist_timezone=specialist_timezone,
            )

            if slot_start_datetime == requested_start_in_specialist_tz:
                return slot

        raise CreateTherapySessionValidationError(
            "Выбранный слот уже занят. Пожалуйста, выберите другое время"
        )

    @staticmethod
    def _get_effective_session_duration_minutes(*, runtime_context, slot_day):
        """Возвращает фактическую длительность сессии на день выбранного старта."""
        return runtime_context["override_session_duration_minutes_by_day"].get(
            slot_day,
            runtime_context["session_duration_minutes"],
        )

    @transaction.atomic
    def execute(self, *, client_user, specialist_profile_id: int, slot_start_iso: str, consultation_type: str) -> dict:
        """Запускает процесс booking-flow и создает встречу."""
        # 1) Запускаем кастомные первоначальные валидации
        validate_client_can_create_therapy_session(client_user=client_user)
        validate_consultation_type_in_therapy_session(consultation_type=consultation_type)
        requested_slot_start_datetime = parse_requested_slot_start(slot_start_iso=slot_start_iso)

        # 2) Получаем специалиста, к которому клиент пытается записаться.
        # На этом этапе backend уже не доверяет данным с фронта "на слово", а проверяет,
        # что профиль специалиста действительно существует в системе.
        specialist_profile = get_specialist_profile_for_booking_therapy_session(
            specialist_profile_id=specialist_profile_id,
        )
        specialist_user = specialist_profile.user

        # 3) Сразу блокируем записи двух участников в БД в стабильном порядке.
        # Это нужно для сценария, когда клиент или специалист почти одновременно пытаются создать
        # пересекающиеся встречи: такая блокировка уменьшает риск гонок при бронировании.
        user_model = get_user_model()
        user_ids_to_lock = sorted([client_user.pk, specialist_user.pk], key=str)
        locked_users = list(
            user_model.objects.select_for_update().filter(pk__in=user_ids_to_lock).order_by("pk")
        )

        if len(locked_users) != 2:
            raise CreateTherapySessionValidationError(
                "Не удалось получить блокировку участников для безопасного создания бронирования."
            )

        # 4) Приводим timezone специалиста к единому tzinfo-формату.
        # Это важно, потому что расписание специалиста считается именно в его локальном времени,
        # а клиент мог выбрать слот, находясь вообще в другом часовом поясе.
        specialist_timezone = normalize_user_timezone(
            timezone_value=getattr(specialist_user, "timezone", None)
        )

        # build_specialist_schedule_runtime_context() - собирает единый runtime-context для booking логики специалиста
        # 5) Собираем единый runtime-context специалиста:
        #   - рабочее правило;
        #   - активные исключения;
        #   - override-параметры на конкретные дни;
        #   - уже существующие занятые интервалы.
        # Это важно, чтобы и отображение расписания, и само бронирование опирались на одну и ту же логику.
        runtime_context = build_specialist_schedule_runtime_context(
            specialist_profile=specialist_profile,
            consultation_type=consultation_type,
        )

        if runtime_context is None:
            raise CreateTherapySessionValidationError(
                "У специалиста нет активного рабочего расписания для бронирования."
            )

        # Use-case получения актуального расписания специалиста (в TZ СПЕЦИАЛИСТА).
        #     Ответственность:
        #         - сгенерировать доменные слоты;
        #         - отфильтровать их по AvailabilityRule / AvailabilityException / Booking;
        #         - вернуть список доступных SlotDTO.
        # 6) Повторно пересчитываем расписание специалиста на backend.
        # Это ключевая защита от ситуации, когда клиент увидел слот на странице несколько секунд назад,
        # но пока нажимал кнопку "Записаться", слот уже успел заняться или перестал подходить по правилам.
        specialist_schedule_use_case = GenerateSpecialistScheduleUseCase(**runtime_context)
        available_slots = specialist_schedule_use_case.execute()

        # 7) Ищем среди актуально доступных стартов именно тот слот, который выбрал клиент.
        # Если такого старта уже нет - значит бронирование нужно прервать и попросить выбрать новое время.
        selected_slot = self._find_matching_available_slot(
            requested_slot_start_datetime=requested_slot_start_datetime,
            specialist_timezone=specialist_timezone,
            available_slots=available_slots,
        )

        # 8) Строим уже реальные datetime начала и конца будущей сессии.
        # Важно:
        #   - start_datetime опирается на выбранный доменный старт;
        #   - end_datetime считается по реальной длительности сессии выбранного типа;
        #   - break_between_sessions здесь НЕ входит в TimeSlot.end_datetime, а используется отдельно
        #     только для логики блокировки следующих доменных стартов.
        slot_start_datetime = self._build_specialist_slot_start_datetime(
            slot=selected_slot,
            specialist_timezone=specialist_timezone,
        )
        effective_session_duration_minutes = self._get_effective_session_duration_minutes(
            runtime_context=runtime_context,
            slot_day=selected_slot.day,
        )
        slot_end_datetime = slot_start_datetime + timedelta(minutes=effective_session_duration_minutes)

        # 9) Дополнительно защищаем клиента от двойной записи на одно и то же время.
        # Даже если слот свободен у специалиста, backend не должен создавать новую сессию,
        # если у самого клиента уже есть другая встреча с пересечением по времени.
        validate_client_has_no_overlapping_therapy_sessions(
            client_user=client_user,
            slot_start_datetime=slot_start_datetime,
            slot_end_datetime=slot_end_datetime,
        )

        # # 10) Формируем понятный заголовок события для календаря клиента.
        # # Название должно сразу объяснять пользователю, что это за встреча и с каким специалистом она связана.
        # specialist_full_name = (
        #     f"{specialist_user.first_name} {specialist_user.last_name}".strip()
        #     or specialist_user.email
        # )
        # event_title = build_booking_therapy_session_title(
        #     specialist_full_name=specialist_full_name,
        #     consultation_type=consultation_type,
        # )

        # 11) Создаем корневую сущность встречи - CalendarEvent.
        # Это "карточка" самой терапевтической сессии, внутри которой потом уже живут слот и участники.
        event = CalendarEvent(
            creator=client_user,
            title="Терапевтическая сессия с психологом",  # title=event_title
            description="",
            event_type="session_couple" if consultation_type == "couple" else "session_individual",
            status="planned",
            visibility="private",
            source="internal",
            is_recurring=False,
        )
        event.full_clean()
        event.save()

        # 12) Создаем TimeSlot как конкретный временной интервал этой встречи.
        # Здесь сохраняем только чистое время сессии без break_between_sessions.
        slot = TimeSlot(
            creator=client_user,
            event=event,
            start_datetime=slot_start_datetime,
            end_datetime=slot_end_datetime,
            status="planned",
            timezone=specialist_timezone,
            meeting_url=None,
            comment=None,
            slot_index=1,
        )
        slot.full_clean()
        slot.save()

        # 13) Фиксируем состав участников на уровне всей встречи.
        # По согласованной бизнес-логике:
        #   - клиент выступает организатором и уже считается accepted;
        #   - специалист получает статус invited.
        event_participants = [
            EventParticipant(
                event=event,
                user=client_user,
                role="organizer",
                status="accepted",
            ),
            EventParticipant(
                event=event,
                user=specialist_user,
                role="participant",
                status="invited",
            ),
        ]

        for participant in event_participants:
            participant.full_clean()
            participant.save()

        # 14) Фиксируем участников и на уровне конкретного временного слота.
        # Это отдельный слой модели, который понадобится для дальнейшей логики проведения встречи,
        # подключения участников, отметок joined_at/left_at и т.д.
        slot_participants = [
            SlotParticipant(
                slot=slot,
                user=client_user,
                role="organizer",
                status="planned",
            ),
            SlotParticipant(
                slot=slot,
                user=specialist_user,
                role="participant",
                status="planned",
            ),
        ]

        for participant in slot_participants:
            participant.full_clean()
            participant.save()

        # 15) Возвращаем результат use-case вызывающему слою.
        # API или web-flow дальше сами решат, как показать пользователю успешное бронирование.
        return {
            "event": event,
            "slot": slot,
            "created_at": timezone.now(),
        }
