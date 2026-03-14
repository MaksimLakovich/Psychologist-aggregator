from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Min, Prefetch
from django.utils import timezone
from django.views.generic import TemplateView

from calendar_engine.models import CalendarEvent, EventParticipant, TimeSlot
from core.services.calendar_slot_time_display import build_calendar_slot_time_display
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin


class ClientPlannedSessionsView(SpecialistMatchingLayoutMixin, LoginRequiredMixin, TemplateView):
    """Контроллер страницы *Мой кабинет / Календарь сессий / Запланированные*.

    Бизнес-смысл страницы:
        - после успешного создания терапевтической сессии клиент должен сразу увидеть, что встреча действительно
          создана;
        - экран показывает запланированные встречи со статусом planned, а также уже начавшиеся встречи со
          статусом started, чтобы клиент не потерял к ним быстрый доступ;
        - layout страницы должен сохраняться в том же режиме (верхнее меню или сайдбар), из которого клиент прошел
          шаги подбора и записи.
    """

    template_name = "core/client_pages/my_account/planned_sessions.html"

    def _build_planned_events(self):
        """Собирает удобную для шаблона проекцию запланированных и уже начавшихся терапевтические сессии."""
        # Берем текущий timezone именно из профиля клиента.
        # Это важно для сценария, когда встреча была создана раньше, а потом клиент сменил свой timezone в профиле:
        # страница должна показывать дату/время уже по новому часовому поясу клиента.
        client_timezone = getattr(self.request.user, "timezone", None)

        # Получаем только те события, которые действительно относятся к клиенту и еще не закончились.
        # Пояснение Django ORM синтаксиса:
        # - participants__user=self.request.user
        #     "__" здесь означает переход по связи между моделями. Т.е., у CalendarEvent есть связанные
        #     participants (EventParticipant) и оставляем те события, где среди участников есть текущий пользователь;
        # - status__in=["planned", "started"]. Т.е., "__in" означает "значение поля входит в список";
        # - slots__end_datetime__gte=timezone.now() - это дополнительная страховка, понятно что у нас проведенные
        #     встречи меняют статус и отсекаются выше на шаге status__in, но для страховки, если не сработал сервис
        #     изменения статусной модели лучше добавить еще такой фильтр.
        #     Здесь идет переход по связи "__": CalendarEvent -> slots (related_name у TimeSlot) -> end_datetime.
        #     "__gte" означает "больше или равно". Т.е., только те события, у которых слот еще не закончился
        events = (
            CalendarEvent.objects.filter(
                participants__user=self.request.user,
                status__in=["planned", "started"],
                slots__end_datetime__gte=timezone.now(),
            )
            # annotate(...) добавляет к каждому событию вычисляемое поле прямо на уровне SQL-запроса.
            # Здесь first_slot_start = минимальное slots__start_datetime.
            # Зачем это нужно:
            #   - у события может быть несколько слотов;
            #   - для списка "Запланированные" нам нужно уметь стабильно сортировать событие по самому раннему слоту
            .annotate(first_slot_start=Min("slots__start_datetime"))
            # prefetch_related(...) заранее подгружает связанные данные отдельными SQL-запросами,
            # чтобы потом в цикле по событиям не делать N дополнительных запросов к БД (исключаем проблему N+1)
            .prefetch_related(
                # Prefetch для slots нужен, чтобы:
                #   - получить все слоты события одним набором;
                #   - сразу отсортировать их по start_datetime;
                #   - потом безопасно взять "основной" слот как самый ранний.
                Prefetch("slots", queryset=TimeSlot.objects.order_by("start_datetime")),
                # Правила повторения подгружаем заранее, чтобы потом без дополнительных запросов
                # показать тип повторяемости события
                Prefetch("recurrences"),
                Prefetch(
                    "participants",
                    # select_related(...) работает для ForeignKey / OneToOne и делает SQL JOIN.
                    # Это позволяет сразу подтянуть:
                    #   - самого user участника;
                    #   - и профиль психолога этого пользователя.
                    # Тогда в шаблоне и в Python-коде дальше не будет лишних обращений в БД
                    queryset=EventParticipant.objects.select_related(
                        "user",
                        "user__psychologist_profile",
                    ).order_by("pk"),
                ),
            )
            # distinct() здесь нужен, потому что из-за JOIN по participants и slots одно и то же событие
            # могло бы повториться в результирующем QuerySet несколько раз
            .distinct()
            # Сначала сортируем по самому раннему слоту встречи, а при одинаковом времени - по дате создания
            .order_by("first_slot_start", "created_at")
        )

        planned_events = []
        # Берем id только что созданной встречи из session и сразу удаляем его оттуда.
        # Это нужно для одноразовой подсветки:
        #   - после redirect клиент видит список своих сессий;
        #   - одна из них только что была создана на предыдущем шаге;
        #   - именно ее мы помечаем как "Только что создано", а при следующем открытии страницы или обновлении
        #   эта подсветка исчезнет, т.е., разово показываем только при создании
        last_created_booking_id = self.request.session.pop("last_created_booking_id", None)

        for event in events:
            # Для карточки списка берем не "самый первый слот вообще", а первый АКТУАЛЬНЫЙ слот:
            #   - либо еще запланированный;
            #   - либо уже начавшийся.
            # Это важно для будущих multi-slot событий.
            #
            # Пример:
            #   - у события "Курс" три урока;
            #   - первый урок уже completed;
            #   - второй урок planned;
            #   - третий урок planned.
            # В таком случае на странице "Запланированные" нужно показывать не первый завершенный урок,
            # а ближайший еще актуальный урок курса.
            #
            # Важно: фильтруем уже загруженный через prefetch набор слотов,
            # чтобы не делать дополнительный SQL-запрос на каждое событие.
            active_slots = [
                slot
                for slot in event.slots.all()
                if slot.status in ["planned", "started"]
            ]

            # TODO: Для будущих multi-slot событий нужно изменить эту строку и логику страницы в целом,
            #  так как сейчас "эта страница = список событий", а если нам нужно показывать multi-slot события,
            #  то, наверное, логично показывать каждый будущий урок (slot) отдельно, а не общее event для всех уроков
            primary_slot = next(iter(active_slots), None)

            # Находим второго участника встречи, чтобы показать клиенту с кем именно у него назначена сессия.
            # Здесь self.request.user - это сам клиент, поэтому ищем участника с другим user_id.
            # TODO: Для будущих групповых событий данная логика также требует переосмысления и доработки
            counterpart_participant = next(
                (
                    participant
                    for participant in event.participants.all()
                    if participant.user_id != self.request.user.pk
                ),
                None,
            )
            counterpart_user = counterpart_participant.user if counterpart_participant else None
            specialist_profile = (
                getattr(counterpart_user, "psychologist_profile", None)
                if counterpart_user
                else None
            )
            counterpart_full_name = (
                f"{counterpart_user.first_name} {counterpart_user.last_name}".strip()
                if counterpart_user
                else ""
            )
            # Превращаем start/end слота в готовые display-значения:
            #   - дату;
            #   - время;
            #   - ISO-строки для month-widget календаря;
            #   - подпись timezone клиента
            slot_display_data = (
                build_calendar_slot_time_display(
                    slot=primary_slot,
                    client_timezone=client_timezone,
                )
                if primary_slot
                else {}
            )
            recurrence_rule = next(iter(event.recurrences.all()), None)

            # Формируем готовую структуру для HTML-шаблона
            planned_events.append(
                {
                    "event": event,
                    "primary_slot": primary_slot,
                    "counterpart_user": counterpart_user,
                    "counterpart_full_name": counterpart_full_name or "Имя не указано",
                    "specialist_profile": specialist_profile,
                    "specialist_photo_url": counterpart_user.avatar_url,
                    "visibility_display": event.get_visibility_display() or "Приватная",
                    "event_type_display": event.get_event_type_display() or "Индивидуальная сессия",
                    "display_date": slot_display_data.get("display_date"),
                    "display_day_key": slot_display_data.get("display_day_key"),
                    "display_time_range": slot_display_data.get("display_time_range"),
                    "display_client_timezone": slot_display_data.get("display_client_timezone"),
                    "display_start_iso": slot_display_data.get("display_start_iso"),
                    "display_end_iso": slot_display_data.get("display_end_iso"),
                    "frequency_display": (
                        recurrence_rule.get_frequency_display()
                        if recurrence_rule and recurrence_rule.frequency
                        else "Разовая встреча"
                    ),
                    "is_recently_created": str(event.id) == last_created_booking_id,
                }
            )

        return planned_events

    def _build_calendar_month_widget_events(self, *, planned_events) -> list[dict]:
        """Готовит компактный JSON-совместимый набор событий для month-widget календаря.

        Бизнес-смысл:
            - виджет справа не должен пересчитывать доменную логику;
            - он получает уже готовые даты встреч клиента и только визуально показывает,
              в какие дни сколько сессий назначено.
        """
        calendar_events = []

        for item in planned_events:
            primary_slot = item.get("primary_slot")
            if primary_slot is None:
                continue

            # Формируем минимальный набор данных, который нужен именно JS-календарю.
            # То есть month-widget не получает всю карточку встречи, а только то,
            # что нужно для отображения дня, месяца и количества встреч на конкретную дату
            calendar_events.append(
                {
                    "id": str(item["event"].id),
                    "title": item["event"].title,
                    "start": item["display_start_iso"],  # нужен для календарного виджета FullCalendar
                    "end": item["display_end_iso"],  # нужен для календарного виджета FullCalendar
                    "status": item["event"].status,
                    "day_key": item["display_day_key"],  # нужен для счетчика встреч по дням в month-widget
                }
            )

        return calendar_events

    def get_context_data(self, **kwargs):
        """Формирует контекст страницы запланированных сессий клиента."""
        context = super().get_context_data(**kwargs)

        context["title_client_account_view"] = "Запланированные сессии на ОПОРА"

        # Применяем тот же layout-режим, который сопровождал клиента на шагах подбора и записи:
        # либо верхнее меню, либо сайдбар
        self._apply_layout_context(context)

        context["current_sidebar_key"] = "session-planned"

        # Сначала собираем все карточки встреч для основной левой колонки страницы (СПИСОК)
        planned_events = self._build_planned_events()
        context["planned_events"] = planned_events

        # Затем из уже подготовленных карточек встреч собираем отдельный компактный набор данных
        # для month-widget календаря в правой колонке (КАЛЕНДАРЬ)
        context["calendar_month_widget_events"] = self._build_calendar_month_widget_events(
            planned_events=planned_events,
        )

        # Начальный месяц виджета тоже выставляем по timezone клиента,
        # чтобы календарь открывался не "по серверу", а по фактическому текущему времени клиента
        context["calendar_widget_initial_date"] = timezone.localtime(
            timezone.now(),
            getattr(self.request.user, "timezone", None),
        ).strftime("%Y-%m-%d")

        return context
