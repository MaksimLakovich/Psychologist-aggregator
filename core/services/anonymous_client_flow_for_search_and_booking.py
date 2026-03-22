"""Сервисный модуль для guest-flow подбора психолога (работа с новым незарегистрированным пользователем).
Здесь хранится в сессии и потом восстанавливается временное состояние нового неавторизованного клиента:
    - его ответы на шаги подбора;
    - выбранный слот;
    - служебные данные для автоматического возврата к бронированию после регистрации (после подтверждения email).
"""

from dataclasses import dataclass
from typing import Any

from django.core import signing
from django.urls import reverse

from calendar_engine.booking.services import normalize_user_timezone
from users.models import Method, Topic

GUEST_MATCHING_STATE_SESSION_KEY = "guest_matching_state_v1"
RESUME_BOOKING_SIGNING_SALT = "core.specialist_matching.resume_booking"
RESUME_BOOKING_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7


def _build_default_guest_state() -> dict[str, Any]:
    """Возвращает базовый пустой черновик guest-anonymous-состояние.

    В агрегаторе это стартовое состояние нового клиента до регистрации:
    общие ответы, личные предпочтения и отложенное бронирование еще не заполнены.

    Пояснение для параметра "pending_booking":
        1. Новый пользователь открыл сайт: pending_booking = None
        2. Он заполнил анкету и дошел до выбора специалиста: pending_booking = None
        3. Он выбрал психолога id=9, слот 2026-03-25T07:00:00+03:00, тип couple, нажал "Записаться", но он еще
        не зарегистрирован. Тогда pending_booking станет примерно таким:
            {
                "specialist_profile_id": 9,
                "slot_start_iso": "2026-03-25T07:00:00+03:00",
                "consultation_type": "couple",
                "layout_mode": "menu",
            }
        4. После регистрации и подтверждения email система читает этот pending_booking и понимает, что:
            "нужно не просто активировать аккаунт, а еще завершить вот эту запись".
    """
    return {
        "general": {
            "first_name": "",
            "email": "",
            "age": None,
            "timezone": "",
            "therapy_experience": False,
        },
        "personal": {
            "preferred_topic_type": "individual",
            "requested_topic_ids": [],
            "has_preferences": False,
            "preferred_ps_gender": [],
            "preferred_ps_age": [],
            "preferred_method_ids": [],
            "has_time_preferences": False,
            "preferred_slots": [],
        },
        "pending_booking": None,  # Ожидающая подтверждения и завершения бронирования сессия/встреча
    }


def get_guest_matching_state(session) -> dict[str, Any]:
    """Достает из session текущее временное состояние нового неавторизованного клиента (guest-anonymous-состояние)
    и приводит его к нормальному полному виду.

    Т.е., функция возвращается уже не "сырое значение из session", а "нормализованное полное состояние/структуру",
    таким образом после этой функции остальные шаги flow могут продолжить работу без ошибок и продолжить запись
    значений от guest-anonymous-user, потому что всегда получают предсказуемую структуру:
        - всегда есть general;
        - всегда есть personal;
        - всегда есть pending_booking;
        - даже если session была пустой или неполной.
    """
    # Session в Django - серверное хранилище данных пользователя.
    # Тут мы пробуем взять из session значение по ключу GUEST_MATCHING_STATE_SESSION_KEY
    state = session.get(GUEST_MATCHING_STATE_SESSION_KEY)
    defaults = _build_default_guest_state()  # Создает эталонный базовый пустой черновик структуры guest-anonymous

    # Если в session нет нормального словаря структуры guest-anonymous, то возвращается чистый дефолт
    if not isinstance(state, dict):
        return defaults

    # Тут берем из session кусок general и personal и если это действительно dict, то накладываем его поверх дефолта:
    # 1) Дефолт:
    # defaults["general"] = {
    #     "first_name": "",
    #     "email": "",
    #     "age": None,
    #     "timezone": "",
    #     "therapy_experience": False,
    # }
    # 2) А из session пришло:
    # general = {
    #     "first_name": "Анна",
    #     "email": "anna@example.com",
    # }
    # 3) После update(general) получится:
    # defaults["general"] = {
    #     "first_name": "Анна",
    #     "email": "anna@example.com",
    #     "age": None,
    #     "timezone": "",
    #     "therapy_experience": False,
    # }
    general = state.get("general")
    if isinstance(general, dict):
        defaults["general"].update(general)

    personal = state.get("personal")
    if isinstance(personal, dict):
        defaults["personal"].update(personal)

    # В pending_booking у нас либо:
    # - None;
    # - либо уже готовый целый словарь paused-booking.
    # Поэтому тут не update, а просто полная замена
    pending_booking = state.get("pending_booking")
    if isinstance(pending_booking, dict):
        defaults["pending_booking"] = pending_booking

    return defaults


def save_guest_matching_state(session, state: dict[str, Any]) -> None:
    """Сохраняет в session весь текущий guest-anonymous-state целиком.

    Вынес в отдельную функцию, чтоб потом не писать этот код дублем каждый раз в тех местах где нужно сохранять:
        - update_guest_general_state();
        - update_guest_personal_state();
        - set_guest_pending_booking();
        - clear_guest_pending_booking().
    """
    session[GUEST_MATCHING_STATE_SESSION_KEY] = state
    session.modified = True


def clear_guest_matching_state(session) -> None:
    """Полностью очищает в session весь текущий guest-anonymous-state целиком.

    Это нужно после успешного завершения сценария по регистрации гостя и когда он стал авторизованным пользователем,
    а система успешно завершила бронь из "pending_booking", чтобы старые ответы и слот не подтягивались в новый заход.
    """
    session.pop(GUEST_MATCHING_STATE_SESSION_KEY, None)
    session.modified = True


def update_guest_general_state(session, *, payload: dict[str, Any]) -> dict[str, Any]:
    """Обновляет в session ответы гостя с первого шага подбора.

    На вход получает уже подготовленный словарь данных из form/view и сохраняет его в блок general.
        - update: заменяет существующие ключи новыми значениями и не трогает ключи, которых в payload нет;
        - payload: собирает все именованные аргументы в один словарь.
    """
    state = get_guest_matching_state(session)  # 1) Достает из session текущее guest-anonymous-состояние
    state["general"].update(payload)  # 2) Обновляет guest-anonymous-состояние
    save_guest_matching_state(session, state)  # 3) Сохраняет в session весь обновленный guest-anonymous-state
    return state


def update_guest_personal_state(session, *, payload: dict[str, Any]) -> dict[str, Any]:
    """Обновляет в session ответы гостя со второго шага подбора.

    На вход получает уже подготовленный словарь данных из form/view и сохраняет его в блок personal.
        - update: заменяет существующие ключи новыми значениями и не трогает ключи, которых в payload нет;
        - payload: собирает все именованные аргументы в один словарь.
    """
    state = get_guest_matching_state(session)
    state["personal"].update(payload)
    save_guest_matching_state(session, state)
    return state


def set_guest_pending_booking(
    session, *, specialist_profile_id: int, slot_start_iso: str, consultation_type: str,
) -> dict[str, Any]:
    """Ставит бронирование guest-anonymous на паузу в session.

    В агрегаторе это точка, где новый клиент уже выбрал специалиста и время, но еще не зарегистрировался и поэтому
    не может завершить запись.
    Сохраняем эти данные, чтоб потом, при успешном завершении guest-anonymous процедуры регистрации, система
    автоматически завершила бронирование и создала событие с данным специалистом на ранее выбранный слот.
    """
    state = get_guest_matching_state(session)
    state["pending_booking"] = {
        "specialist_profile_id": int(specialist_profile_id),
        "slot_start_iso": slot_start_iso,
        "consultation_type": consultation_type,
        "layout_mode": "menu",  # мы сразу четко указываем menu потому что guest не могут работать через sidebar
    }
    save_guest_matching_state(session, state)
    return state["pending_booking"]


def get_guest_pending_booking(session) -> dict[str, Any] | None:
    """Возвращает отложенное бронирование guest-anonymous, если оно есть.

    Это данные в session по выбору специалиста и слота, которые были сохранены перед отправкой guest-anonymous
    на login/register, чтоб потом, при успешном завершении guest-anonymous процедуры регистрации, система
    автоматически завершила бронирование и создала событие с данным специалистом на ранее выбранный слот.
    """
    return get_guest_matching_state(session).get("pending_booking")


def clear_guest_pending_booking(session) -> None:
    """Удаляет только paused-booking в session, не трогая ответы гостя на шаги подбора.

    Полезно, когда нужно сбросить выбранный слот, но оставить ранее заполненные данные анкеты.
    """
    state = get_guest_matching_state(session)
    state["pending_booking"] = None
    save_guest_matching_state(session, state)


# TODO: нужно подумать и, возможно, гостя отправлять сразу на новую страницу где "Уже регистрировался ранее или нет?"
def get_guest_data_for_registration(session) -> dict[str, Any]:
    """Подготавливает initial-значения для страницы регистрации.

    Благодаря этому новый клиент не вводит заново email, имя и возраст, которые уже указал на шаге подбора.
    """
    general = get_guest_matching_state(session)["general"]
    return {
        "email": general.get("email", ""),
        "first_name": general.get("first_name", ""),
        "age": general.get("age"),
    }


# TODO: нужно подумать и, возможно, гостя отправлять сразу на новую страницу где "Уже регистрировался ранее или нет?"
def get_guest_data_for_login(session) -> dict[str, Any]:
    """Подготавливает initial-значение для страницы входа.

    Благодаря этому новый клиент не вводит заново email, которые уже указал на шаге подбора.
    """
    general = get_guest_matching_state(session)["general"]
    return {
        "username": general.get("email", ""),
    }


@dataclass
class AnonymousSessionUser:
    """Легковесное представление гостя как пользователя.

    Нужен, чтобы downstream-логика поиска/подбора и формирования рабочего расписания могла работать с "гостем"
    почти так же, как с обычным зарегистрированным и авторизованным "AppUser", без создания записи в БД.
    """

    first_name: str
    email: str
    age: int | None
    timezone: Any


class AnonymousClientProfile:
    """Временный профиль клиента для незарегистрированного гостя (guest-anonymous).

    Собирает ответы гостя из session в объект, похожий на ClientProfile, но без участия БД для этого, чтобы
    существующая логика подбора специалиста и его рабочего расписания работала как у зарегистрированного клиента.
    """

    def __init__(self, state: dict[str, Any]):
        """Собирает session-черновик гостя в объект, похожий на ClientProfile.
        На выходе получаем структуру с user, предпочтениями и ленивыми queryset по темам/методам."""
        general = state["general"]
        personal = state["personal"]

        timezone_value = general.get("timezone") or None
        effective_timezone = (
            normalize_user_timezone(timezone_value=timezone_value)
            if timezone_value
            else None
        )

        self.user = AnonymousSessionUser(
            first_name=general.get("first_name", "") or "",
            email=general.get("email", "") or "",
            age=general.get("age"),
            timezone=effective_timezone,
        )
        self.therapy_experience = bool(general.get("therapy_experience", False))
        self.preferred_topic_type = personal.get("preferred_topic_type", "individual") or "individual"
        self.has_preferences = bool(personal.get("has_preferences", False))
        self.preferred_ps_gender = list(personal.get("preferred_ps_gender", []) or [])
        self.preferred_ps_age = list(personal.get("preferred_ps_age", []) or [])
        self.has_time_preferences = bool(personal.get("has_time_preferences", False))
        self.preferred_slots = list(personal.get("preferred_slots", []) or [])
        self._requested_topic_ids = list(personal.get("requested_topic_ids", []) or [])
        self._preferred_method_ids = list(personal.get("preferred_method_ids", []) or [])

    @property
    def requested_topics(self):
        """Возвращает queryset тем, которые гость выбрал на шаге личных вопросов."""
        return Topic.objects.filter(id__in=self._requested_topic_ids)

    @property
    def preferred_methods(self):
        """Возвращает queryset методов, которые гость отметил как предпочтительные."""
        return Method.objects.filter(id__in=self._preferred_method_ids)


def build_guest_profile(session) -> AnonymousClientProfile:
    """Строит временный профиль гостя (guest-anonymous) из текущего состояния в session.

    Это основной вход для бизнес-логики подбора, когда пользователь еще не зарегистрирован.
    """
    return AnonymousClientProfile(get_guest_matching_state(session))


def apply_guest_state_to_user(*, user, session) -> None:
    """Переносит guest-anonymous-состояние в реального пользователя, если новый пользователь успешно завершил
    процесс регистрации и подтвердил email.

    Так новый клиент не теряет уже введенные данные и сразу получает заполненный профиль клиента в БД.
    """
    state = get_guest_matching_state(session)
    general = state["general"]
    personal = state["personal"]

    user.first_name = general.get("first_name", "") or user.first_name
    user.age = general.get("age") or user.age
    user.timezone = general.get("timezone") or user.timezone
    user.save(update_fields=["first_name", "age", "timezone"])

    profile = user.client_profile
    profile.therapy_experience = bool(general.get("therapy_experience", False))
    profile.preferred_topic_type = personal.get("preferred_topic_type", "individual") or "individual"
    profile.has_preferences = bool(personal.get("has_preferences", False))
    profile.preferred_ps_gender = list(personal.get("preferred_ps_gender", []) or [])
    profile.preferred_ps_age = list(personal.get("preferred_ps_age", []) or [])
    profile.has_time_preferences = bool(personal.get("has_time_preferences", False))
    profile.preferred_slots = list(personal.get("preferred_slots", []) or [])
    profile.save(
        update_fields=[
            "therapy_experience",
            "preferred_topic_type",
            "has_preferences",
            "preferred_ps_gender",
            "preferred_ps_age",
            "has_time_preferences",
            "preferred_slots",
        ]
    )
    profile.requested_topics.set(personal.get("requested_topic_ids", []) or [])
    profile.preferred_methods.set(personal.get("preferred_method_ids", []) or [])


def build_signed_booking_token(*, user, session) -> str | None:
    """Создает и подписывает данные через Django signing и возвращает токен ("безопасная записка для системы, которую
    можно безопасно положить в email-ссылку") для продолжения paused-бронирования после завершения email верификации
    и подтверждения регистрации.

    Токен кладется в ссылку из письма и позволяет безопасно восстановить выбранный гостем слот.
    """
    # 1) Берем из session отложенную бронь (paused-booking)
    pending_booking = get_guest_pending_booking(session)
    if not pending_booking:
        return None

    # 2) Собираем payload: все именованные аргументы в один словарь
    payload = {
        "user_pk": str(user.pk),
        "specialist_profile_id": pending_booking["specialist_profile_id"],
        "slot_start_iso": pending_booking["slot_start_iso"],
        "consultation_type": pending_booking["consultation_type"],
        "layout_mode": pending_booking.get("layout_mode", "menu"),
    }

    # 3) Превращаем словарь в signed token.
    # - "django.core.signing" это встроенный механизм Django для:
    #     - сериализовать данные в строку
    #     - подписать их криптографической подписью
    #     - signing это просто подпись (просто проверка, что никто не изменил потом данные), а не шифрование
    #     - потом уметь проверить, что их никто не подменил
    # - "signing.dumps()" берет Python-объект, сериализует его, потом подписывает и возвращает строку:
    #   payload -> строка JSON/serialized data -> подпись -> итоговый token
    # - "salt" это дополнительная "метка контекста". Это значит, что токен относится именно к resume-booking,
    #   а не к чему-то другому. Это нужно, чтобы токены из одного сценария нельзя было случайно использовать
    #   как токены другого сценария, т.е. это дополнительное разделение контекстов подписи.
    #   Простыми словами: salt - это имя конкретного типа токена.
    # - "compress=True" для того, если данные получаются большими по размеру, то выполнится их сжатие перед упаковкой.
    #   Токен может попадать в URL и поэтому чем он короче, тем лучше
    # 4) Эта строка (токен) потом добавляется в ссылку email в send_verification_email().
    #   После клика по письму вызывается "signing.loads". Т.е.:
    #     - берем строку токена
    #     - проверяется подпись
    #     - проверяет salt
    #     - проверяет срок жизни
    #     - если все ок, возвращает исходный словарь pending_booking и завершается paused-booking
    return signing.dumps(payload, salt=RESUME_BOOKING_SIGNING_SALT, compress=True)


def load_signed_booking_token(
        token: str | None, *, max_age: int = RESUME_BOOKING_TOKEN_MAX_AGE_SECONDS,
) -> dict[str, Any] | None:
    """Проверяет и распаковывает через Django signing токен по paused-бронирования из email-ссылки.

    Если токен битый, подмененный или просроченный, метод безопасно возвращает None.
    """
    if not token:
        return None

    try:
        payload = signing.loads(token, salt=RESUME_BOOKING_SIGNING_SALT, max_age=max_age)
    except signing.BadSignature:
        return None
    except signing.SignatureExpired:
        return None

    return payload if isinstance(payload, dict) else None


def build_choice_psychologist_url(*, reset: bool = True):
    """Собирает URL возврата на шаг выбора психолога для guest-resume-flow.

    Используется после подтверждения email, если система попыталась автоматически завершить paused-booking,
    но выбранный слот уже недоступен (например, его забронировал другой клиент или слот уже в прошлом).
    Тогда пользователя нужно вернуть на шаг выбора психолога и времени в режиме нового повторного выбора.
    """
    query = "?layout=menu"
    if reset:
        # reset=1 нужен, чтобы экран открылся как новый повторный выбор, а не пытался продолжить работать
        # на старом выбранном психологе/слоте
        query = f"{query}&reset=1"
    return f"{reverse('core:choice-psychologist')}{query}"
