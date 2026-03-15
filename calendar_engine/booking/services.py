from zoneinfo import ZoneInfo

from django.utils import timezone

from calendar_engine.models import AvailabilityException, AvailabilityRule, TimeSlot
from calendar_engine.services import normalize_range
from calendar_engine.booking.exceptions import CreateTherapySessionValidationError
from users.models import PsychologistProfile


def get_specialist_profile_for_booking_therapy_session(*, specialist_profile_id: int) -> PsychologistProfile:
    """Возвращает профиль специалиста для сценария бронирования терапевтической сессии.

    Бизнес-смысл:
        - клиент записывается не просто к пользователю, а к конкретному профилю специалиста;
        - поэтому для booking-flow источником истины выступает именно PsychologistProfile.
    """
    try:
        return PsychologistProfile.objects.select_related("user").get(pk=specialist_profile_id)
    except PsychologistProfile.DoesNotExist as exc:
        raise CreateTherapySessionValidationError("Выбранный специалист не найден.") from exc


def normalize_user_timezone(*, timezone_value):
    """Нормализует timezone пользователя к объекту tzinfo.

    В проекте timezone может храниться как строка или как готовый tzinfo-объект.
    Перед расчетом расписания и сравнением слотов backend приводит это поле к одному предсказуемому виду.
    """
    if timezone_value is None:
        raise CreateTherapySessionValidationError(
            "У пользователя не указан timezone. Невозможно корректно выполнить booking-операцию."
        )

    if hasattr(timezone_value, "utcoffset"):
        return timezone_value

    return ZoneInfo(str(timezone_value))


def _get_effective_time_windows_for_day(*, rule: AvailabilityRule, exceptions, day) -> list[tuple]:
    """Возвращает итоговые рабочие окна специалиста на конкретный календарный день.

    Бизнес-смысл:
        - live-индикатору не нужны доменные слоты и не нужен их фильтр;
        - ему нужен только прямой ответ на вопрос:
          "Какие рабочие окна реально действуют у специалиста сегодня?"

    Правила:
        1) Если есть активное исключение `unavailable`, день полностью закрыт.
        2) Если есть активное исключение `override`, оно полностью переопределяет базовые окна правила.
        3) Если исключений на день нет, используются обычные окна из AvailabilityRule.

    Важно:
        - в проекте одно активное правило;
        - exceptions сюда уже приходят только для текущего дня.
    """
    for exception in exceptions:
        if exception.exception_type == "unavailable":
            return []

        if exception.exception_type == "override":
            override_windows = [
                (window.override_start_time, window.override_end_time)
                for window in exception.time_windows.all()
                if window.override_start_time is not None and window.override_end_time is not None
            ]
            return override_windows

    if day.weekday() not in set(rule.weekdays):
        return []

    return [
        (window.start_time, window.end_time)
        for window in rule.time_windows.all()
    ]


def build_specialist_live_indicator(*, specialist_profile: PsychologistProfile | None) -> dict:
    """Возвращает готовый display-контракт индикатора статуса специалиста для UI.

    Бизнес-смысл:
        - на страницах клиента индикатор над аватаром специалиста не должен мигать "всегда просто так";
        - он должен отражать текущее реальное состояние специалиста с учетом:
            1) его рабочего расписания;
            2) текущего времени в часовом поясе специалиста;
            3) факта, идет ли у него прямо сейчас активная встреча.

    Правила поведения индикатора:
        - красный без ping:
            специалист сейчас вне рабочего дня/времени;
        - зеленый с ping:
            специалист сейчас в рабочем окне и свободен;
        - желтый с ping:
            специалист сейчас в рабочем окне, но у него уже идет встреча.

    Возвращает:
        dict c уже готовыми для шаблона полями:
            - state;
            - should_ping;
            - dot_color;
            - ping_color;
            - title.
    """
    # 1) Индикатор "Не работает" от которого будем отталкиваться.
    # ДЛЯ ИНФО: Тут необходимо использовать реальные цвета (#BE185D), а не Tailwind class, потому что utility-классы,
    # который собираются динамически на runtime, Tailwind может не отработать при сборке CSS
    offline_indicator = {
        "state": "offline",
        "should_ping": False,
        "dot_color": "#BE185D",  # pink-700
        "ping_color": "",
        "label": "Не рабочее время",
        "title": "Специалист сейчас вне рабочего времени",
    }

    if specialist_profile is None:
        return offline_indicator

    current_datetime = timezone.now()

    # 2) Берем активное рабочее расписание специалиста
    active_rule = (
        AvailabilityRule.objects.filter(
            creator=specialist_profile.user,
            is_active=True,
        )
        .prefetch_related("time_windows")
        .first()
    )

    if active_rule is None:
        return offline_indicator

    timezone_value = active_rule.timezone or getattr(specialist_profile.user, "timezone", None)
    effective_timezone = (
        normalize_user_timezone(timezone_value=timezone_value)
        if timezone_value is not None
        else timezone.get_default_timezone()
    )
    current_specialist_datetime = current_datetime.astimezone(effective_timezone)
    current_specialist_day = current_specialist_datetime.date()

    # Активное правило может не покрывать текущую дату/время, например, если его период еще не начался
    # или уже закончился. В таком случае для текущего момента специалист считаем вне рабочего периода
    if not (
        active_rule.rule_start <= current_specialist_day
        and (active_rule.rule_end is None or active_rule.rule_end >= current_specialist_day)
    ):
        return offline_indicator

    # 3) Подтягиваем только актуальные на текущий день исключения и считаем итоговые рабочие окна дня.
    # Для этого использую _get_effective_time_windows_for_day() - которая возвращает итоговые рабочие окна специалиста
    exceptions = AvailabilityException.objects.filter(
        rule=active_rule,
        is_active=True,
        exception_start__lte=current_specialist_day,
        exception_end__gte=current_specialist_day,
    ).prefetch_related("time_windows")

    allowed_time_windows = _get_effective_time_windows_for_day(
        rule=active_rule,
        exceptions=exceptions,
        day=current_specialist_day,
    )

    # normalize_range() возвращает локальный диапазон окна как datetime без timezone.
    # Поэтому текущее локальное время специалиста тоже переводим в naive-local вид,
    # чтобы корректно сравнить "попадаем ли мы сейчас внутрь рабочего окна".
    current_specialist_datetime_naive = current_specialist_datetime.replace(tzinfo=None)

    is_working_now = False

    for window_start, window_end in allowed_time_windows:
        window_start_datetime, window_end_datetime = normalize_range(
            current_specialist_day,
            window_start,
            window_end,
        )
        if window_start_datetime <= current_specialist_datetime_naive < window_end_datetime:
            is_working_now = True
            break

    if not is_working_now:
        return offline_indicator

    # Если специалист сейчас в рабочем окне, дополнительно проверяем, не идет ли у него активная встреча.
    # Здесь не полагаемся только на status="started", потому что в реальной жизни статус может обновиться с лагом,
    # а сам интервал встречи уже фактически начался.
    has_session_now = TimeSlot.objects.filter(
        status__in=["planned", "started"],
        slot_participants__user=specialist_profile.user,
        start_datetime__lte=current_datetime,
        end_datetime__gt=current_datetime,
    ).exists()

    # 4) Индикатор "Работает", но сейчас занят
    if has_session_now:
        return {
            "state": "in_session_now",
            "should_ping": True,
            "dot_color": "#E3A008",  # yellow-500
            "ping_color": "#FACC15",  # yellow-400
            "label": "Занят",
            "title": "Специалист сейчас на сессии",
        }

    # 5) Индикатор "Работает" и сейчас свободен
    return {
        "state": "available_now",
        "should_ping": True,
        "dot_color": "#34D399",  # emerald-400
        "ping_color": "#6EE7B7",  # emerald-300
        "label": "Рабочее время",
        "title": "Специалист сейчас в рабочем времени и свободен",
    }


# def build_booking_therapy_session_title(*, specialist_full_name: str, consultation_type: str) -> str:
#     """Формирует понятное пользователю название терапевтической сессии."""
#     normalized_specialist_name = specialist_full_name.strip() or "специалистом"
#
#     if consultation_type == "couple":
#         return f"Парная сессия с {normalized_specialist_name}"
#
#     return f"Индивидуальная сессия с {normalized_specialist_name}"
