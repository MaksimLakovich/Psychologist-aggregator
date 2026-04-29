from django.urls import reverse

from calendar_engine.booking.services import build_specialist_live_indicator
from calendar_engine.lifecycle.services.slot_status_display import \
    build_calendar_slot_status_display
from core.services.calendar_slot_time_display import \
    build_calendar_slot_time_display


# Типы событий, которые в текущей бизнес-модели считаются терапевтической сессией
THERAPY_SESSION_EVENT_TYPES = {"session_individual", "session_couple"}


class BaseClientEventCardAdapter:
    """Базовый общий adapter краткой карточки события для страницы клиента "Мой календарь".

    Бизнес-смысл:
        - страница "Мой календарь" должна показывать разные виды событий в одном списке:
            - терапевтические сессии;
            - вебинары;
            - курсы;
            - интервизии/супервизии и так далее;
        - у всех этих событий есть общий минимум данных для краткой карточки:
            - название;
            - дата и время;
            - длительность;
            - статус;
            - тип события;
            - признак "это уже архивная карточка или еще активная";
        - этот базовый adapter собирает именно такой общий минимум;
        - если конкретному типу события нужны дополнительные блоки, он наследуется от этого класса
          и дополняет карточку своими данными.

    Пример:
        - вебинару может понадобиться "ведущий" и "количество мест";
        - курсу может понадобиться "урок 2 из 8";
        - терапевтической сессии нужен психолог, его фото, live-индикатор и ссылка на detail-страницу сессии.
    """

    def __init__(
        self,
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
    ):
        """Запоминает входные данные, из которых будет собрана краткая карточка события.

        Бизнес-смысл:
            - ClientEventsView уже нашел событие пользователя и выбрал слот, который нужно показать в списке;
            - adapter не ходит заново искать событие, а получает готовые данные и превращает их в удобный
              контракт для HTML-шаблона;
            - так список календаря остается общим, а особенности разных типов событий живут в adapter-ах.
        """
        self.event = event
        self.slot = slot
        self.viewer_user = viewer_user
        self.viewer_timezone = viewer_timezone
        self.current_datetime = current_datetime
        self.layout_query = layout_query
        self.last_created_booking_id = last_created_booking_id
        self.specialist_indicator_cache = specialist_indicator_cache
        self.force_archived_card = force_archived_card

    def build(self) -> dict:
        """Формирует общий набор данных для краткой карточки события в списке "Мой календарь".

        Бизнес-смысл:
            - HTML-шаблон не должен сам вычислять, как красиво показать дату, статус, длительность или архивность;
            - шаблон получает уже готовые поля и просто рисует карточку;
            - если событие пока неизвестного будущего типа, базовая карточка все равно может безопасно показаться,
              но кнопка detail-страницы будет недоступна до появления отдельного adapter-а.

        Пример:
            - для будущего вебинара без готовой detail-страницы клиент увидит время, название, тип события и статус;
            - вместо ошибочного перехода на терапевтическую сессию кнопка покажет "Детали скоро".
        """
        # Готовим дату и время по timezone пользователя, который открыл календарь.
        # Например, один и тот же слот должен отображаться клиенту в его локальном времени,
        # а не в техническом времени сервера или специалиста.
        slot_display_data = build_calendar_slot_time_display(
            slot=self.slot,
            client_timezone=self.viewer_timezone,
        )
        # Если событие повторяется, показываем человекочитаемую частоту.
        # Если правил повторения нет, карточка считается разовой встречей.
        recurrence_rule = next(iter(self.event.recurrences.all()), None)
        # Для базового adapter-а detail_url по умолчанию отсутствует.
        # Конкретные типы событий сами решают, куда должна вести кнопка "Посмотреть".
        detail_url = self._build_detail_url()

        return {
            "event": self.event,
            "slot": self.slot,
            "detail_url": detail_url,
            "detail_is_available": detail_url is not None,
            "detail_unavailable_label": "Детали скоро",
            "event_kind": "event",
            "counterpart_user": None,
            "counterpart_full_name": "Детали события",
            "counterpart_caption": self.event.get_event_type_display() or "Событие",
            "specialist_profile": None,
            "specialist_live_indicator": build_specialist_live_indicator(specialist_profile=None),
            "show_specialist_live_indicator": False,
            "specialist_photo_url": "/static/images/menu/user-circle.svg",
            "visibility_display": self.event.get_visibility_display() or "Приватная",
            "event_type_display": self.event.get_event_type_display() or "Событие",
            "status_display": build_calendar_slot_status_display(slot=self.slot),
            "duration_minutes": self._get_duration_minutes(),
            "display_date": slot_display_data.get("display_date"),
            "display_day_key": slot_display_data.get("display_day_key"),
            "display_start_time": slot_display_data.get("display_start_time"),
            "display_end_time": slot_display_data.get("display_end_time"),
            "display_time_range": slot_display_data.get("display_time_range"),
            "display_month_short": slot_display_data.get("display_month_short"),
            "display_day_number": slot_display_data.get("display_day_number"),
            "display_weekday": slot_display_data.get("display_weekday"),
            "display_client_timezone": slot_display_data.get("display_client_timezone"),
            "display_start_iso": slot_display_data.get("display_start_iso"),
            "display_end_iso": slot_display_data.get("display_end_iso"),
            "is_today": slot_display_data.get("is_today", False),
            "frequency_display": (
                recurrence_rule.get_frequency_display()
                if recurrence_rule and recurrence_rule.frequency
                else "Разовая встреча"
            ),
            "is_recently_created": str(self.event.id) == self.last_created_booking_id,
            "is_archived_card": self._is_archived_card(),
            "can_open_meeting_url": self._can_open_meeting_url(),
        }

    def _build_detail_url(self):
        """Возвращает ссылку на detail-страницу события.

        Бизнес-смысл:
            - у разных типов событий будут разные detail-страницы;
            - базовый adapter не знает, куда вести клиента для будущего вебинара или курса;
            - поэтому по умолчанию возвращаем None, и шаблон покажет не ссылку, а безопасную disabled-кнопку.
        """
        return None

    def _get_duration_minutes(self):
        """Считает длительность отображаемого слота в минутах.

        Бизнес-смысл:
            - в краткой карточке клиенту важно быстро понять, сколько времени займет событие;
            - для терапевтической сессии это может быть 50/120 минут;
            - для будущего вебинара или урока курса это будет длительность соответствующего слота.
        """
        return int((self.slot.end_datetime - self.slot.start_datetime).total_seconds() // 60)

    def _is_archived_card(self):
        """Определяет, должна ли карточка выглядеть как архивная.

        Бизнес-смысл:
            - активные события визуально выделяются и могут давать быстрый доступ к видеочату;
            - завершенные/отмененные события остаются в истории, но показываются более спокойным архивным стилем;
            - force_archived_card нужен для режима "Показать завершенные", где весь список открыт как архив.
        """
        return (
            self.force_archived_card
            or self.slot.status in ["completed", "cancelled"]
            or self.slot.end_datetime < self.current_datetime
        )

    def _can_open_meeting_url(self):
        """Определяет, можно ли показать кнопку быстрого перехода в видеочат.

        Бизнес-смысл:
            - кнопку "Видеочат" имеет смысл показывать только пока встреча еще актуальна;
            - после завершения или отмены события ссылка на созвон не должна быть главным действием в карточке;
            - если у будущего типа события тоже будет meeting_url, базовая карточка уже умеет показать эту кнопку.
        """
        return bool(
            self.slot.meeting_url
            and self.slot.status in ["planned", "started"]
            and self.slot.end_datetime >= self.current_datetime
        )


class TherapySessionClientEventCardAdapter(BaseClientEventCardAdapter):
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

    def build(self) -> dict:
        """Дополняет базовую карточку данными, специфичными для терапевтической сессии.

        Бизнес-смысл:
            - сначала собираем общий минимум карточки через BaseClientEventCardAdapter;
            - затем добавляем то, что имеет смысл только для therapy session:
                - имя психолога;
                - профиль психолога;
                - аватар;
                - подпись "Психолог • Онлайн/Офлайн";
                - активную кнопку "Посмотреть" с маршрутом на detail-страницу сессии.
        """
        # Сначала получаем универсальную карточку: дата, время, статус, длительность, тип события.
        # Это та общая основа, которая подойдет и будущему вебинару, и курсу, и супервизии.
        card = super().build()
        # Для терапевтической сессии второй участник относительно клиента = психолог.
        # Это правило относится только к therapy session, поэтому оно живет здесь, а не в общей view.
        counterpart_user = self._get_counterpart_user()
        specialist_profile = (
            getattr(counterpart_user, "psychologist_profile", None)
            if counterpart_user
            else None
        )
        specialist_profile_id = getattr(specialist_profile, "pk", None)

        # В одном списке у клиента может быть несколько сессий с одним и тем же психологом.
        # Чтобы не пересчитывать live-индикатор специалиста повторно для каждой карточки, используем cache на request.
        if specialist_profile_id not in self.specialist_indicator_cache:
            self.specialist_indicator_cache[specialist_profile_id] = build_specialist_live_indicator(
                specialist_profile=specialist_profile,
            )

        # Готовим имя специалиста для краткой карточки.
        # Если в профиле пользователя имя еще не заполнено, шаблон получит мягкий fallback "Имя не указано".
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
                "detail_is_available": True,
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
        - эта функция решает, какой именно "сборщик карточки" использовать.

    Пример:
        - session_individual/session_couple -> TherapySessionClientEventCardAdapter;
        - будущий webinar -> WebinarClientEventCardAdapter;
        - будущий course -> CourseClientEventCardAdapter;
        - пока adapter-а нет -> BaseClientEventCardAdapter.
    """
    if event.event_type in THERAPY_SESSION_EVENT_TYPES:
        return TherapySessionClientEventCardAdapter
    return BaseClientEventCardAdapter


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
          на чужую detail-страницу.
    """
    adapter_class = get_client_event_card_adapter_class(event)
    return adapter_class(
        event=event,
        slot=slot,
        viewer_user=viewer_user,
        viewer_timezone=viewer_timezone,
        current_datetime=current_datetime,
        layout_query=layout_query,
        last_created_booking_id=last_created_booking_id,
        specialist_indicator_cache=specialist_indicator_cache,
        force_archived_card=force_archived_card,
    ).build()
