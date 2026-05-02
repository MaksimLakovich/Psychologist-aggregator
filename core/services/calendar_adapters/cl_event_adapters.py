from django.urls import reverse

from calendar_engine.booking.services import build_specialist_live_indicator
from core.services.calendar_adapters.base_event_adapters import \
    BaseCalendarEventCardAdapter


# Типы событий, которые в текущей бизнес-модели считаются терапевтической сессией.
# Остальные типы событий получат свои adapter-ы позже, когда появится их бизнес-логика
THERAPY_SESSION_EVENT_TYPES = {"session_individual", "session_couple"}


class TherapySessionClientEventCardAdapter(BaseCalendarEventCardAdapter):
    """Adapter карточки терапевтической сессии в общем календаре клиента.

    Бизнес-смысл:
        - терапевтическая сессия на стороне клиента отличается от абстрактного события тем,
          что клиенту важно видеть "с кем именно у меня встреча";
        - поэтому поверх базовой карточки добавляем:
            - второго участника встречи = психолога;
            - фото специалиста;
            - формат работы специалиста;
            - live-индикатор специалиста;
            - ссылку на существующую detail-страницу терапевтической сессии.
    """

    def __init__(self, *, specialist_indicator_cache, **kwargs):
        """Запоминает клиентский cache live-индикаторов специалистов.

        Бизнес-смысл:
            - один клиент может иметь в списке несколько сессий с одним и тем же психологом;
            - live-индикатор специалиста можно посчитать один раз за request и переиспользовать;
            - эта оптимизация относится именно к клиентской карточке therapy session, поэтому не лежит
              в общей календарной базе.
        """
        super().__init__(**kwargs)
        self.specialist_indicator_cache = specialist_indicator_cache

    def build(self) -> dict:
        """Дополняет базовую карточку данными, специфичными для терапевтической сессии.

        Бизнес-смысл:
            - сначала собираем общий минимум карточки через BaseCalendarEventCardAdapter;
            - затем добавляем то, что имеет смысл только для therapy session:
                - имя психолога;
                - профиль психолога;
                - аватар;
                - подпись "Психолог • Онлайн/Офлайн";
                - активную кнопку "Посмотреть" с маршрутом на detail-страницу сессии.
        """
        # Сначала получаем универсальную карточку: дата, время, статус, длительность, тип события.
        # Это та общая основа, которая подойдет и будущему вебинару, и курсу, и супервизии
        card = super().build()
        # Для терапевтической сессии второй участник относительно клиента = психолог.
        # Это правило относится только к therapy session, поэтому оно живет здесь, а не в общей view
        counterpart_user = self._get_counterpart_user()
        specialist_profile = (
            getattr(counterpart_user, "psychologist_profile", None)
            if counterpart_user
            else None
        )
        specialist_profile_id = getattr(specialist_profile, "pk", None)

        # В одном списке у клиента может быть несколько сессий с одним и тем же психологом.
        # Чтобы не пересчитывать live-индикатор специалиста повторно для каждой карточки, используем cache на request
        if specialist_profile_id not in self.specialist_indicator_cache:
            self.specialist_indicator_cache[specialist_profile_id] = build_specialist_live_indicator(
                specialist_profile=specialist_profile,
            )

        # Готовим имя специалиста для краткой карточки.
        # Если в профиле пользователя имя еще не заполнено, шаблон получит мягкий fallback "Имя не указано"
        counterpart_full_name = (
            f"{counterpart_user.first_name} {counterpart_user.last_name}".strip()
            if counterpart_user
            else ""
        )
        # Формат работы показываем рядом с ролью: например "Психолог • Онлайн".
        # Это часть именно терапевтической карточки, а не универсального события.
        therapy_format_display = (
            specialist_profile.get_therapy_format_display()
            if specialist_profile
            else "Онлайн"
        )

        # Обновляем универсальную карточку therapy-specific данными.
        # Благодаря этому HTML-шаблон остается единым: он не знает про внутренние правила каждого типа события.
        card.update(
            {
                "detail_url": self._build_detail_url(),
                "event_kind": "therapy_session",
                "counterpart_user": counterpart_user,
                "counterpart_full_name": counterpart_full_name or "Имя не указано",
                "counterpart_caption": f"Психолог • {therapy_format_display}",
                "specialist_profile": specialist_profile,
                "specialist_live_indicator": self.specialist_indicator_cache[specialist_profile_id],
                "show_specialist_live_indicator": True,
                "specialist_photo_url": (
                    counterpart_user.avatar_url
                    if counterpart_user
                    else "/static/images/menu/user-circle.svg"
                ),
            }
        )
        return card

    def _build_detail_url(self):
        """Формирует маршрут на detail-страницу терапевтической сессии.

        Бизнес-смысл:
            - кнопка "Посмотреть" в карточке therapy session должна вести на уже реализованный экран сессии;
            - layout_query сохраняет режим интерфейса клиента: меню или сайдбар;
            - для будущих типов событий будут свои adapter-ы и свои маршруты detail-страниц.
        """
        return (
            f"{reverse('core:client-therapy-session-detail', kwargs={'event_id': self.event.id})}"
            f"{self.layout_query}"
        )

    def _get_counterpart_user(self):
        """Находит психолога как второго участника терапевтической сессии.

        Бизнес-смысл:
            - therapy session в текущей системе всегда состоит из двух сторон:
                - клиент;
                - специалист;
            - клиент открывает свой календарь, поэтому "другой участник" этой сессии и есть психолог,
              которого нужно показать в краткой карточке.
        """
        counterpart_participant = next(
            (
                participant
                for participant in self.event.participants.all()
                if participant.user_id != self.viewer_user.pk
            ),
            None,
        )
        return counterpart_participant.user if counterpart_participant else None


def get_client_event_card_adapter_class(event):
    """Выбирает adapter краткой карточки по типу события.

    Бизнес-смысл:
        - "Мой календарь" остается одной общей страницей для всех событий клиента;
        - но каждый тип события может иметь свою подачу в карточке и свой маршрут на detail-страницу;
        - эта функция решает, какой именно "сборщик карточки" использовать;
        - если тип события еще не поддержан отдельным adapter-ом, карточка останется безопасной базовой.

    Пример:
        - session_individual/session_couple -> TherapySessionClientEventCardAdapter;
        - будущий webinar -> WebinarClientEventCardAdapter;
        - будущий course -> CourseClientEventCardAdapter;
        - пока adapter-а нет -> BaseCalendarEventCardAdapter.
    """
    if event.event_type in THERAPY_SESSION_EVENT_TYPES:
        return TherapySessionClientEventCardAdapter
    return BaseCalendarEventCardAdapter


def build_client_event_card(
    *,
    event,
    slot,
    viewer_user,
    viewer_timezone,
    current_datetime,
    layout_query,
    last_created_booking_id,
    specialist_indicator_cache,
    force_archived_card=False,
) -> dict:
    """Публичная функция сборки краткой карточки события для ClientEventsView.

    Бизнес-смысл:
        - view не должна знать детали каждого event_type;
        - view передает событие, выбранный слот, текущего пользователя и layout;
        - функция сама выбирает подходящий adapter и возвращает готовый словарь для HTML-шаблона.

    Пример:
        - если событие является терапевтической сессией, вернется карточка с психологом и ссылкой на session-detail;
        - если это будущий тип события без adapter-а, вернется базовая карточка без опасного перехода
          на какую-либо неподходящую detail-страницу.
    """
    adapter_class = get_client_event_card_adapter_class(event)
    adapter_kwargs = {
        "event": event,
        "slot": slot,
        "viewer_user": viewer_user,
        "viewer_timezone": viewer_timezone,
        "current_datetime": current_datetime,
        "layout_query": layout_query,
        "recently_created_event_id": last_created_booking_id,
        "force_archived_card": force_archived_card,
    }

    # Cache live-индикаторов нужен только клиентской карточке therapy session.
    # Базовая календарная карточка не знает про психолога и не должна получать role-specific данные.
    if adapter_class is TherapySessionClientEventCardAdapter:
        adapter_kwargs["specialist_indicator_cache"] = specialist_indicator_cache

    return adapter_class(**adapter_kwargs).build()
