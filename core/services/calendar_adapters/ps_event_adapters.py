from django.urls import reverse

from core.services.calendar_adapters.base_event_adapters import \
    BaseCalendarEventCardAdapter


# Типы событий, которые в текущей бизнес-модели считаются терапевтической сессией.
# Остальные типы событий получат свои adapter-ы позже, когда появится их бизнес-логика
THERAPY_SESSION_EVENT_TYPES = {"session_individual", "session_couple"}


class TherapySessionPsychologistEventCardAdapter(BaseCalendarEventCardAdapter):
    """Adapter карточки терапевтической сессии в календаре специалиста.

    Бизнес-смысл:
        - специалист смотрит на ту же терапевтическую сессию, что и клиент, но с другой стороны;
        - специалисту в карточке важно видеть клиента, с которым назначена встреча;
        - поэтому общую календарную базу дополняем role-специфическими данными специалиста:
            - клиент как вторая сторона встречи;
            - аватар клиента;
            - подпись "Клиент";
            - маршрут на detail-страницу сессии специалиста.
    """

    def build(self) -> dict:
        """Дополняет базовую карточку данными, специфичными для терапевтической сессии.

        Бизнес-смысл:
            - сначала собираем общий календарный минимум: дату, время, статус, длительность, тип события;
            - затем заменяем клиентскую-перспективу на specialist-перспективу:
                - заголовок "Терапевтическая сессия с клиентом";
                - имя клиента;
                - ссылка на detail-экран специалиста.
        """
        # Сначала получаем универсальную карточку: дата, время, статус, длительность, тип события.
        # Это та общая основа, которая подойдет и будущему вебинару, и курсу, и супервизии
        card = super().build()
        # Для терапевтической сессии второй участник относительно психолога = клиент.
        # Это правило относится только к therapy session, поэтому оно живет здесь, а не в общей view
        counterpart_user = self._get_counterpart_user()
        # Готовим имя специалиста для краткой карточки.
        # Если в профиле пользователя имя еще не заполнено, шаблон получит мягкий fallback "Имя клиента не указано"
        counterpart_full_name = (
            f"{counterpart_user.first_name} {counterpart_user.last_name}".strip()
            if counterpart_user
            else ""
        )

        card.update(
            {
                "title_display": "Терапевтическая сессия с клиентом",
                "detail_url": self._build_detail_url(),
                "event_kind": "therapy_session",
                "counterpart_user": counterpart_user,
                "counterpart_full_name": counterpart_full_name or "Имя клиента не указано",
                "counterpart_caption": "Клиент",
                "show_counterpart_photo": False,
            }
        )
        return card

    def _build_detail_url(self):
        """Формирует маршрут на detail-страницу терапевтической сессии специалиста.

        Бизнес-смысл:
            - кнопка "Посмотреть" в карточке therapy session должна вести на экран сессии для специалиста;
            - специалисту нужен свой экран, где он управляет ссылкой на встречу и итогами сессии;
            - layout_query сохраняет тот же режим интерфейса: меню или сайдбар.
        """
        return (
            f"{reverse('core:psychologist-therapy-session-detail', kwargs={'event_id': self.event.id})}"
            f"{self.layout_query}"
        )

    def _get_counterpart_user(self):
        """Находит клиента как второго участника терапевтической сессии.

        Бизнес-смысл:
            - therapy session в текущей системе состоит из двух сторон:
                - клиент;
                - специалист;
            - специалист открывает свой календарь, поэтому "другой участник" этой встречи и есть клиент,
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


def get_psychologist_event_card_adapter_class(event):
    """Выбирает adapter краткой карточки по типу события для календаря специалиста.

    Бизнес-смысл:
        - "Мой календарь" остается одной общей страницей для всех событий клиента;
        - но каждый тип события может иметь свою подачу в карточке и свой маршрут на detail-страницу;
        - эта функция решает, какой именно "сборщик карточки" использовать;
        - если тип события еще не поддержан отдельным adapter-ом, карточка останется безопасной базовой.

    Пример:
        - session_individual/session_couple -> TherapySessionPsychologistEventCardAdapter;
        - будущий webinar -> WebinarPsychologistEventCardAdapter;
        - будущий course -> CoursePsychologistEventCardAdapter;
        - пока adapter-а нет -> BaseCalendarEventCardAdapter.
    """
    if event.event_type in THERAPY_SESSION_EVENT_TYPES:
        return TherapySessionPsychologistEventCardAdapter
    return BaseCalendarEventCardAdapter


def build_psychologist_event_card(
    *,
    event,
    slot,
    viewer_user,
    viewer_timezone,
    current_datetime,
    layout_query,
    force_archived_card=False,
) -> dict:
    """Публичная функция сборки краткой карточки события для PsychologistEventsView.

    Бизнес-смысл:
        - view специалиста не должна знать детали каждого event_type;
        - view передает событие и выбранный слот;
        - функция сама выбирает подходящий adapter и возвращает готовый словарь для HTML-шаблона.

    Пример:
        - если событие является терапевтической сессией, вернется карточка с клиентом и ссылкой на session-detail;
        - если это будущий тип события без adapter-а, вернется базовая карточка без опасного перехода
          на какую-либо неподходящую detail-страницу.
    """
    adapter_class = get_psychologist_event_card_adapter_class(event)
    return adapter_class(
        event=event,
        slot=slot,
        viewer_user=viewer_user,
        viewer_timezone=viewer_timezone,
        current_datetime=current_datetime,
        layout_query=layout_query,
        force_archived_card=force_archived_card,
    ).build()
