from calendar_engine.lifecycle.services.slot_status_display import \
    build_calendar_slot_status_display
from core.services.calendar_slot_time_display import \
    build_calendar_slot_time_display


class BaseCalendarEventCardAdapter:
    """Базовый общий adapter краткой карточки события в календаре для любого пользователя системы (клиент/специалист)
    и для любого вида события.

    Бизнес-смысл:
        - и клиент, и специалист в будущем будут открывать один по смыслу экран "Мой календарь";
        - внутри этого календаря могут быть разные типы событий:
            - терапевтическая сессия;
            - вебинар;
            - курс;
            - супервизия;
            - интервизия и так далее;
        - у всех этих событий есть общий минимум данных для краткой карточки:
            - название;
            - дата и время;
            - длительность;
            - статус;
            - тип события;
            - признак "это уже архивная карточка или еще активная";
        - этот базовый общий adapter собирает только такой общий минимум параметров и не знает, кто именно
        смотрит карточку события: клиент или специалист.

    Пример:
        - клиентская карточка терапевтической сессии добавит к этой базе психолога;
        - карточка специалиста добавит к этой базе клиента;
        - карточка вебинара добавит ведущего и количество мест и так далее.
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
        recently_created_event_id=None,
        force_archived_card=False,
    ):
        """Запоминает входные данные, из которых будет собрана краткая карточка события.

        Бизнес-смысл:
            - view для role-специфики уже нашла событие пользователя и выбрала слот, который нужно показать в списке;
            - adapter не ищет событие заново, а получает готовые данные и превращает их в удобный контракт
              для HTML-шаблона;
            - так общая календарная база остается одной, а особенности ролей живут в client/psychologist adapter-ах.
        """
        self.event = event
        self.slot = slot
        self.viewer_user = viewer_user
        self.viewer_timezone = viewer_timezone
        self.current_datetime = current_datetime
        self.layout_query = layout_query
        self.recently_created_event_id = recently_created_event_id
        self.force_archived_card = force_archived_card

    def build(self) -> dict:
        """Формирует общий набор данных для краткой карточки события в календаре.

        Бизнес-смысл:
            - HTML-шаблон не должен сам вычислять, как красиво показать дату, статус, длительность или архивность;
            - шаблон получает уже готовые поля и просто формирует карточку;
            - если событие пока неизвестного будущего типа, базовая карточка все равно может безопасно показаться,
              но кнопка detail-страницы будет недоступна до появления отдельного adapter-а.

        Пример:
            - будущий вебинар без готовой detail-страницы покажет время, название, тип события и статус;
            - вместо ошибочного перехода на терапевтическую сессию кнопка покажет "Детали скоро".
        """
        # Готовим дату и время по timezone пользователя, который открыл календарь.
        # Например, один и тот же слот должен отображаться клиенту или специалисту в их локальном времени,
        # а не в техническом времени сервера
        slot_display_data = build_calendar_slot_time_display(
            slot=self.slot,
            client_timezone=self.viewer_timezone,
        )
        # Если событие повторяется, показываем человекочитаемую частоту.
        # Если правил повторения нет, карточка считается разовой встречей
        recurrence_rule = next(iter(self.event.recurrences.all()), None)
        # Для общей базы detail_url по умолчанию отсутствует.
        # Конкретные типы событий и роли сами решают, куда должна вести кнопка "Посмотреть".
        detail_url = self._build_detail_url()

        return {
            "event": self.event,
            "slot": self.slot,
            "title_display": self.event.title,
            "detail_url": detail_url,
            "detail_is_available": detail_url is not None,
            "detail_unavailable_label": "Детали скоро",
            "event_kind": "event",
            "counterpart_user": None,
            "counterpart_full_name": "Детали события",
            "counterpart_caption": self.event.get_event_type_display() or "Событие",
            "specialist_profile": None,
            "specialist_live_indicator": self._build_empty_live_indicator(),
            "show_specialist_live_indicator": False,
            "show_counterpart_photo": True,
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
            "is_recently_created": str(self.event.id) == self.recently_created_event_id,
            "is_archived_card": self._is_archived_card(),
            "can_open_meeting_url": self._can_open_meeting_url(),
        }

    def _build_detail_url(self):
        """Возвращает ссылку на detail-страницу события.

        Бизнес-смысл:
            - у разных ролей и типов событий будут разные detail-страницы;
            - общая календарная база не знает, куда вести клиента для вебинара или специалиста для супервизии;
            - поэтому по умолчанию возвращаем None, и шаблон покажет не ссылку, а безопасную disabled-кнопку.
        """
        return None

    def _build_empty_live_indicator(self):
        """Возвращает нейтральный live-индикатор для событий, где он не нужен.

        Бизнес-смысл:
            - live-индикатор психолога имеет смысл в клиентской карточке терапевтической сессии;
            - для базового события, вебинара или будущего курса такого индикатора может не быть;
            - шаблон получает безопасную пустую структуру, но не показывает ее без явного флага.
        """
        return {
            "state": "not_applicable",
            "should_ping": False,
            "dot_color": "",
            "ping_color": "",
            "label": "",
            "title": "",
        }

    def _get_duration_minutes(self):
        """Считает длительность отображаемого слота в минутах.

        Бизнес-смысл:
            - в краткой карточке пользователю важно быстро понять, сколько времени займет событие;
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
