from zoneinfo import ZoneInfo

from calendar_engine.booking.exceptions import \
    CreateTherapySessionValidationError
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


# def build_booking_therapy_session_title(*, specialist_full_name: str, consultation_type: str) -> str:
#     """Формирует понятное пользователю название терапевтической сессии."""
#     normalized_specialist_name = specialist_full_name.strip() or "специалистом"
#
#     if consultation_type == "couple":
#         return f"Парная сессия с {normalized_specialist_name}"
#
#     return f"Индивидуальная сессия с {normalized_specialist_name}"
