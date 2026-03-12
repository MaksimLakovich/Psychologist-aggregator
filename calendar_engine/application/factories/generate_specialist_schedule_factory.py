from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils.timezone import now

from calendar_engine.application.mappers.exception_mapper import \
    map_exceptions_to_domain
from calendar_engine.application.mappers.rule_mapper import map_rule_to_domain
from calendar_engine.application.use_cases.specialist_schedule import \
    GenerateSpecialistScheduleUseCase
from calendar_engine.constants import DAYS_AHEAD_FOR_SHOW_SCHEDULE
from calendar_engine.domain.availability.domain_slot_generator import \
    DomainSlotGenerator
from calendar_engine.domain.availability.get_user_slots import \
    AvailabilitySlotFilter
from calendar_engine.models import (AvailabilityException, AvailabilityRule,
                                    TimeSlot)
from users.models import PsychologistProfile


def _iter_days(date_from: date, date_to: date):
    """Вспомогательный генератор календарных дней (включительно).
    Просто разворачивает диапазон дат в список конкретных дней, например:
        exception_start = 2026-03-10
        exception_end = 2026-03-12
    Тогда _iter_days() вернет:
        2026-03-10
        2026-03-11
        2026-03-12

    Нужен для сценария, когда одно исключение действует не один день, а диапазон дат.
    Тогда мы можем развернуть диапазон в словарь по каждому календарному дню и позже быстро понять,
    нужно ли в конкретный день переопределять minimum booking notice.
    """
    current = date_from

    while date_to >= current:
        yield current
        current += timedelta(days=1)


def _build_override_break_between_sessions_by_day(exceptions) -> dict:
    """Собирает словарь override_break_between_sessions из AvailabilityException по календарным дням.

    Override_break_between_sessions нужен не только в _build_all_override_maps(),
    но и в _build_specialist_busy_intervals(), поэтому правильнее иметь одну точку правды для такого переопределения.

    Возвращает:
        - словарь вида {date: minutes}, где для каждого календарного дня хранится актуальный
          override_break_between_sessions из AvailabilityException.
    """
    override_break_between_sessions_minutes_by_day = {}

    for exception in exceptions:
        if exception.exception_type != "override":
            continue

        if exception.override_break_between_sessions is None:
            continue

        # Записываем override_break_between_sessions по каждой дате исключения, потому что use-case и busy-логика
        # смотрят не на exception целиком, а на конкретный календарный день.
        for day in _iter_days(exception.exception_start, exception.exception_end):
            override_break_between_sessions_minutes_by_day[day] = exception.override_break_between_sessions

    return override_break_between_sessions_minutes_by_day


def _build_all_override_maps(*, rule, exceptions, consultation_type: str) -> dict:
    """Собирает словари override-параметров из AvailabilityException по календарным дням
    и base-параметры из AvailabilityRule.

    Бизнес-смысл:
        - доменная временная сетка слотов остается общей для всех специалистов, согласно DomainPolicy;
        - но на конкретный день в AvailabilityException специалист может временно поменять:
            - override_session_duration выбранного типа сессии;
            - override_break_between_sessions;
            - override_minimum_booking_notice_hours.
        - поэтому use-case расписания должен быстро получать уже готовые словари по дням.
    """
    override_minimum_booking_notice_hours_by_day = {}
    override_session_duration_minutes_by_day = {}
    override_break_between_sessions_minutes_by_day = _build_override_break_between_sessions_by_day(
        exceptions=exceptions,
    )

    for exception in exceptions:
        if exception.exception_type != "override":
            continue

        # Определяем какой тип сессии будем использовать при расчете доступности специалиста - individual / couple
        override_duration_value = (
            exception.override_session_duration_couple
            if consultation_type == "couple"
            else exception.override_session_duration_individual
        )

        # Записываем актуальные override-параметры
        for day in _iter_days(exception.exception_start, exception.exception_end):

            if override_duration_value is not None:
                override_session_duration_minutes_by_day[day] = override_duration_value

            if exception.override_minimum_booking_notice_hours is not None:
                override_minimum_booking_notice_hours_by_day[day] = exception.override_minimum_booking_notice_hours

    # Записываем актуальные base-параметры в session_duration_couple / session_duration_individual
    base_session_duration_minutes = (
        rule.session_duration_couple
        if consultation_type == "couple"
        else rule.session_duration_individual
    )

    return {
        "session_duration_minutes": base_session_duration_minutes,
        "break_between_sessions_minutes": rule.break_between_sessions or 0,
        "minimum_booking_notice_hours": rule.minimum_booking_notice_hours,
        "override_session_duration_minutes_by_day": override_session_duration_minutes_by_day,
        "override_break_between_sessions_minutes_by_day": override_break_between_sessions_minutes_by_day,
        "override_minimum_booking_notice_hours_by_day": override_minimum_booking_notice_hours_by_day,
    }


def _build_specialist_busy_intervals(
    *,
    specialist_profile: PsychologistProfile,
    specialist_tz,
    rule,
    exceptions,
) -> list[tuple[datetime, datetime]]:
    """Строит список уже занятых интервалов специалиста. Т.е., функция нужна для одной конкретной задачи:
    “Определить какие уже существующие встречи специалиста должны сделать часть доменных стартов (слотов)
    недоступными в его расписании”

    Важно:
        - TimeSlot хранит только чистое время сессии;
        - TimeSlot.end_datetime хранит только чистое окончание сессии;
        - но для доступности нам нужен не только конец сессии, а конец занятого интервала.
          Занятый интервал = end_datetime + break_between_sessions;
        - для блокировки следующих доменных стартов, нам нужно дополнительно прибавить break_between_sessions к
          продолжительности сессии, чтоб определить сколько доменных слотов необходимо выделить под это
          (например, если сессия у специалиста =50 мин и перерыв между =30 мин, то это занимает 2 слота, а не один).

    Т.е., функция НЕ считает новые слоты, а считает уже существующую занятость специалиста в виде списка интервалов:
        [
            (busy_start_1, busy_end_1),
            (busy_start_2, busy_end_2),
            ...
        ]
    А потом GenerateSpecialistScheduleUseCase проверяет:
        если новый доменный старт (слот) пересекается с любым таким busy interval, значит этот старт (слот)
        нельзя показывать как доступный.
    """
    # 1) Ограничиваем горизонт чтения БД только тем периодом, который реально влияет на UI отображаемое расписание,
    # т.е., в карточке специалиста в блоке "Расписание" мы устанавливаем настройку DAYS_AHEAD_FOR_SHOW_SCHEDULE = 9,
    # значит не нужно тянуть из БД всю историю сессий специалиста без пользы, а достаточно только для этих 9 дней
    schedule_horizon_end = datetime.combine(
        now().astimezone(specialist_tz).date() + timedelta(days=DAYS_AHEAD_FOR_SHOW_SCHEDULE + 1),
        time(0, 0),
        tzinfo=specialist_tz,
    )
    schedule_horizon_start = datetime.combine(
        now().astimezone(specialist_tz).date() - timedelta(days=1),
        time(0, 0),
        tzinfo=specialist_tz,
    )
    # 2) Получаем готовый словарь override_break_between_sessions по дням
    override_break_between_sessions_minutes_by_day = _build_override_break_between_sessions_by_day(
        exceptions=exceptions,
    )

    # 3) Берем только реальные активные слоты специалиста, которые уже занимают его календарь. Поэтому
    # события "completed"/"cancelled" здесь не нужны, потому что они не должны блокировать доменные слоты
    specialist_slots = (
        TimeSlot.objects.filter(
            status__in=["planned", "started"],
            slot_participants__user=specialist_profile.user,
            start_datetime__gte=schedule_horizon_start,
            start_datetime__lt=schedule_horizon_end,
        )
        .distinct()
        .order_by("start_datetime")
    )

    # 4) Собираем итоговые busy intervals специалиста.
    # Это не "новые слоты", а именно интервалы занятого времени, которые потом нужны только для того,
    # чтобы скрыть конфликтующие доменные старты в UI-расписании.
    # busy_interval для специалиста считается как интервал:
    # - от slot.start_datetime
    # - до slot.end_datetime + break_between_sessions_minutes
    busy_intervals = []

    for slot in specialist_slots:
        # Переводим slot в timezone специалиста, потому что:
        # 1) override_break_between_sessions определяется по локальному дню специалиста;
        # 2) все дальнейшие сравнения в расписании потом тоже идут в TZ специалиста.
        slot_start_datetime = slot.start_datetime.astimezone(specialist_tz)
        slot_end_datetime = slot.end_datetime.astimezone(specialist_tz)
        slot_day = slot_start_datetime.date()

        # Если на этот день есть override_break_between_sessions - берем его.
        # Иначе используем базовое правило break_between_sessions из AvailabilityRule у специалиста
        break_between_sessions_minutes = override_break_between_sessions_minutes_by_day.get(
            slot_day,
            rule.break_between_sessions or 0,
        )

        # Добавляем busy interval как "чистая сессия + обязательный перерыв после нее".
        # Это нужно для сценариев, когда сам TimeSlot уже закончился, но следующий доменный старт еще нельзя
        # показывать клиенту, потому что специалист заложил себе время на отдых/подготовку
        busy_intervals.append(
            (
                slot_start_datetime,
                slot_end_datetime + timedelta(minutes=break_between_sessions_minutes),
            )
        )

    return busy_intervals


def build_specialist_schedule_runtime_context(
    *,
    specialist_profile: PsychologistProfile,
    consultation_type: str = "individual",
) -> dict | None:
    """Собирает единый runtime-context для availability и booking логики специалиста.

    Почему это отдельная функция, а не сразу в build_generate_specialist_schedule_use_case()?
        - и read-only расписание (просто отображение доступных слотов в детальной карточке специалиста в "Расписание")
          и booking (функционал бронирования и создания событий) должны опираться на одну и ту же трактовку
          duration / break / overrides / уже существующих броней;
        - если собирать эти данные в двух местах, которые по сути идентичны, то в availability и booking
          возникнет риск расхождения.
    """
    if consultation_type not in ("individual", "couple"):
        raise ValueError("consultation_type должен быть либо 'individual', либо 'couple'")

    # 1) Получаем активное правило доступности специалиста
    rule = (
        AvailabilityRule.objects
        .filter(
            creator=specialist_profile.user,
            is_active=True,
        )
        .first()
    )

    # Без активного правила специалист считается недоступным
    if rule is None:
        return None

    # 2) Получаем все активные исключения для этого правила
    exceptions = AvailabilityException.objects.filter(
        rule=rule,
        is_active=True,
    )

    # 3) Адаптируем Django-модели → доменные объекты
    domain_rule = map_rule_to_domain(rule)
    domain_exceptions = map_exceptions_to_domain(exceptions)

    # 4) Фильтруем все возможные доменные слоты по индивидуальным правилам доступности специалиста
    slot_filter = AvailabilitySlotFilter(
        rule=domain_rule,
        exceptions=domain_exceptions,
    )

    # 5) Определяем дату старта генерации В timezone СПЕЦИАЛИСТА, где astimezone(self.timezone) - это метод, который
    # говорит: "И пересчитай это время для данного часового пояса".
    specialist_timezone = getattr(specialist_profile.user, "timezone", None)
    if specialist_timezone:
        specialist_tz = ZoneInfo(str(specialist_timezone))
        current_specialist_time = now().astimezone(specialist_tz)
    else:
        current_specialist_time = now()
    date_from = current_specialist_time.date()

    # 6) Собираем словари override-параметров из AvailabilityException по конкретным дням
    # и base-параметры из AvailabilityRule.
    # Это нужно для сценария, когда специалист на общий период работает по одному правилу, но на отдельные
    # даты хочет показывать ближайшие слоты только за другое количество часов до старта.
    override_maps = _build_all_override_maps(
        rule=rule,
        exceptions=exceptions,
        consultation_type=consultation_type,
    )
    busy_intervals = _build_specialist_busy_intervals(
        specialist_profile=specialist_profile,
        specialist_tz=current_specialist_time.tzinfo,
        rule=rule,
        exceptions=exceptions,
    )

    # 7) Генератор доменных слотов
    slot_generator = DomainSlotGenerator()

    return {
        "slot_generator": slot_generator,
        "slot_filter": slot_filter,
        "date_from": date_from,
        "days_ahead": DAYS_AHEAD_FOR_SHOW_SCHEDULE,
        "current_datetime": current_specialist_time,
        "busy_intervals": busy_intervals,
        **override_maps,
    }


def build_generate_specialist_schedule_use_case(
    specialist_profile: PsychologistProfile,
    consultation_type: str = "individual",
) -> GenerateSpecialistScheduleUseCase | None:
    """Factory финальной сборки use-case генерации расписания специалиста.

    Возвращает:
        - use-case, если у специалиста есть активное правило;
        - None, если специалист сейчас недоступен.

    Важно:
        - консультационный тип влияет не на доменную сетку, а на проверку доступности старта;
        - поэтому use-case принимает consultation_type и применяет его только при проверке
          duration / break / бронирований поверх общей доменной сетки.
    """
    runtime_context = build_specialist_schedule_runtime_context(
        specialist_profile=specialist_profile,
        consultation_type=consultation_type,
    )

    if runtime_context is None:
        return None

    return GenerateSpecialistScheduleUseCase(**runtime_context)
