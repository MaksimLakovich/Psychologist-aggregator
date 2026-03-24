from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max, Min, Prefetch, Q
from django.utils.dateparse import parse_date
from django.utils.formats import date_format
from django.utils import timezone
from django.views.generic import TemplateView

from calendar_engine.booking.services import build_specialist_live_indicator
from calendar_engine.models import CalendarEvent, EventParticipant, TimeSlot
from core.services.calendar_event_slot_selector import get_event_active_slot, get_event_completed_slot
from core.services.calendar_slot_time_display import build_calendar_slot_time_display
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin


class ClientEventsView(SpecialistMatchingLayoutMixin, LoginRequiredMixin, TemplateView):
    """Контроллер страницы *Мой кабинет / Мой календарь*.

    Бизнес-смысл страницы:
        - после успешного создания терапевтической сессии клиент должен сразу увидеть, что встреча действительно
          создана;
        - экран по умолчанию показывает запланированные встречи со статусом planned, а также уже начавшиеся
          встречи со статусом started, чтобы клиент не потерял к ним быстрый доступ;
        - на том же экране клиент может переключиться на прошедшие события, не уходя в отдельный подпункт меню;
        - layout страницы должен сохраняться в том же режиме (верхнее меню или сайдбар), из которого клиент прошел
          шаги подбора и записи.
    """

    template_name = "core/client_pages/my_account/events.html"

    def get_context_data(self, **kwargs):
        """Формирует контекст единой страницы календаря событий клиента.

        Бизнес-смысл:
            - одна и та же страница решает 3 пользовательских сценария:
                - показать ближайшие активные встречи;
                - показать прошедшие встречи;
                - показать встречи только за один выбранный день из month-widget календаря;
            - поэтому здесь собираем все сигналы интерфейса:
                - какой режим списка сейчас открыт;
                - какой текст должен быть в шапке;
                - какую кнопку показать для возврата в основной режим;
                - какие данные передать в правый календарный виджет.
        """
        context = super().get_context_data(**kwargs)

        # Вспомогательная функция, которая определяет, хочет ли клиент видеть архив вместо активных событий
        show_completed = self._should_show_completed_events()
        # Вспомогательная функция, которая возвращает выбранный кликом день в month-widget календаря
        selected_calendar_day = self._get_selected_calendar_day()
        # Применяем тот же layout-режим, который сопровождал клиента на шагах подбора и записи: меню или сайдбар
        self._apply_layout_context(context)

        context["title_client_account_view"] = "Календарь событий на ОПОРА"
        context["current_sidebar_key"] = "all-events"
        context["show_completed"] = show_completed
        context["selected_calendar_day"] = selected_calendar_day
        # selected_calendar_day_display нужен только для формирования человекочитаемой шапки страницы.
        # Например:
        #   - клиент нажал в month-виджете календаря на день "2026-03-25;
        #   - в шапке страницы показываем не технический YYYY-MM-DD, а "События 25 марта".
        context["selected_calendar_day_display"] = (
            date_format(selected_calendar_day, "j E")
            if selected_calendar_day
            else ""
        )

        # ВАРИАНТ 1:
        # Если клиент кликнул конкретный день в month-виджете, страница переходит в режим "показать все по этой дате":
        #   - формируется подходящая шапка/описание страницы
        #   - формируется подходящая кнопка для возврата на все события
        #   - собирается query-строка с обязательным layout и опциональными параметрами
        if selected_calendar_day:
            context["sessions_toggle_label"] = "Показать запланированные"
            context["sessions_toggle_query"] = self._build_layout_query()
            context["page_heading_prefix"] = "События"
            context["page_heading_description"] = (
                "Ниже отображаются все ваши встречи, назначенные на выбранный день календаря"
            )

        # ВАРИАНТ 2:
        # Если клиент в календаре не выбирал день, то оставляем обычное поведение страницы: либо все активные встречи,
        # либо архив (в зависимости от переключателя режима):
        #   - формируется подходящая шапка/описание страницы
        #   - формируется подходящая кнопка для переключения между архивными и активными событиями
        #   - собирается query-строка с обязательным layout и опциональными параметрами
        else:
            context["sessions_toggle_label"] = (
                "Показать запланированные"
                if show_completed
                else "Показать завершенные"
            )
            context["sessions_toggle_query"] = self._build_layout_query(
                sessions_scope=None if show_completed else "completed"
            )
            context["page_heading_prefix"] = "Прошедшие" if show_completed else "Запланированные"
            context["page_heading_description"] = (
                "Ниже отображаются все завершенные встречи, вы можете посмотреть детали прошлых событий"
                if show_completed
                else "Ниже отображаются все ваши ближайшие встречи, которые были успешно созданы в приложении"
            )

        # С помощью вспомогательной функции, в начале собираем все встречи для левой колонки страницы (СПИСОК)
        client_events = self._get_client_events(
            show_completed=show_completed,
            selected_calendar_day=selected_calendar_day,
        )

        context["client_events"] = client_events
        # С помощью вспомогательной функции, на month-виджете календаря показываем активные и завершенные события,
        # чтобы клиент видел общую картину по дням календаря даже при переключении между режимами списка
        context["calendar_month_widget_events"] = self._build_calendar_month_widget_events()
        # Начальный месяц виджета выставляем по timezone клиента, чтобы календарь открывался не "по серверу",
        # а по фактическому текущему времени клиента
        context["calendar_widget_initial_date"] = timezone.localtime(
            timezone.now(),
            getattr(self.request.user, "timezone", None) or timezone.get_default_timezone(),
        ).strftime("%Y-%m-%d")
        # Подписываем календарный виджет тем же timezone, по которому уже показаны сами карточки встреч
        context["calendar_widget_timezone_display"] = str(
            getattr(self.request.user, "timezone", None) or timezone.get_default_timezone()
        )
        # Передаем базовую query-строку для клика по дню в календаре.
        # JS потом просто добавит к ней selected_day=YYYY-MM-DD, сохранив при этом текущий layout страницы.
        context["calendar_day_click_query"] = self._build_layout_query()

        return context

    def _should_show_completed_events(self) -> bool:
        """Определяет, хочет ли клиент видеть архив вместо активных встреч.

        Бизнес-смысл:
            - по умолчанию страница открывается в режиме ближайших активных сессий;
            - если клиент нажал кнопку "Показать завершенные", в query приходит sessions_scope=completed;
            - этот helper превращает query-параметр в понятный флаг для всей view-логики.
        """
        return self.request.GET.get("sessions_scope") == "completed"

    def _get_selected_calendar_day(self):
        """Возвращает день, который клиент выбрал кликом в month-виджете календаря.

        Бизнес-смысл:
            - month-виджет показывает не только загрузку по дням, но и позволяет отфильтровать список встреч слева;
            - если клиент кликнул на день с badge, JS передает selected_day=YYYY-MM-DD;
            - здесь превращаем эту строку в нормальный date-объект, с которым дальше уже удобно работать во view.
        """
        raw_day = (self.request.GET.get("selected_day") or "").strip()
        if not raw_day:
            return None
        return parse_date(raw_day)

    def _get_client_events(self, *, show_completed: bool, selected_calendar_day):
        """Собирает удобную для шаблона проекцию активных, завершенных или выбранных по дню сессий клиента.

        Бизнес-смысл:
            - шаблон страницы не должен сам решать, какие события считать активными, архивными
              или подходящими под фильтр по выбранному дню;
            - эта функция заранее приводит все сценарии к одному HTML-контракту карточки встречи;
            - благодаря этому шаблон просто отображает готовые поля и не тащит на себя бизнес-логику фильтрации.
        """
        # Берем текущий timezone именно из профиля клиента.
        # Это важно для сценария, когда встреча была создана раньше, а потом клиент сменил свой timezone в профиле:
        # страница должна показывать дату/время уже по новому часовому поясу клиента.
        client_timezone = getattr(self.request.user, "timezone", None)
        current_datetime = timezone.now()

        # ШАГ 1: Получаем только те события, которые действительно относятся к клиенту.
        # Пояснение Django ORM синтаксиса:
        #   - participants__user=self.request.user
        #       "__" здесь означает переход по связи между моделями. Т.е., у CalendarEvent есть связанные
        #       participants (EventParticipant) и оставляем те события, где среди участников есть текущий пользователь
        events = (CalendarEvent.objects.filter(
            participants__user=self.request.user,
        )
        # ???
        .annotate(
            latest_slot_end=Max("slots__end_datetime"),
        ))

        # ШАГ 2: Фильтруем события в зависимости от пользовательского запроса. Три сценария:
        # 1) Для фильтра по конкретному календарному дню берем весь набор сессий клиента: активные и уже завершенные:
        #   - клиент нажал день в calendar-widget;
        #   - значит ему нужно показать все события этого дня, а не только активные или только архив
        if selected_calendar_day:
            events = events.filter(
                Q(status__in=["planned", "started", "completed"]) | Q(latest_slot_end__lt=current_datetime)
            ).annotate(
                # annotate(...) добавляет к каждому событию вычисляемое поле прямо на уровне SQL-запроса.
                # Здесь first_slot_start = минимальное slots__start_datetime.
                # Зачем это нужно:
                #   - у события может быть несколько слотов;
                #   - для списка "Запланированные" нужно уметь стабильно сортировать событие по самому раннему слоту
                first_slot_start=Min("slots__start_datetime")
            )
        # 2) Для фильтра и показа всех АРХИВНЫХ событий
        elif show_completed:
            events = events.filter(
                Q(status="completed") | Q(latest_slot_end__lt=current_datetime)
            ).annotate(
                # annotate(...) добавляет к каждому событию вычисляемое поле прямо на уровне SQL-запроса.
                # Для архива нужен не самый ранний, а самый свежий завершенный слот, чтобы сверху были последние
                # прошедшие встречи клиента
                first_slot_start=Max(
                    "slots__start_datetime",
                    filter=Q(slots__status="completed") | Q(slots__end_datetime__lt=current_datetime),
                )
            )
        # 3) Для фильтра и показа всех ЗАПЛАНИРОВАННЫХ событий
        else:
            # Пояснение Django ORM синтаксиса:
            #   - status__in=["planned", "started"]. Т.е., "__in" означает "значение поля входит в список";
            #   - slots__end_datetime__gte=timezone.now() - это дополнительная страховка, понятно что у нас
            #       проведенные встречи меняют статус и отсекаются выше на шаге status__in, но для страховки,
            #       если не сработал сервис изменения статусной модели лучше добавить еще такой фильтр.
            #       Здесь идет переход по связи "__": CalendarEvent -> slots (related_name у TimeSlot) -> end_datetime
            #       "__gte" означает "больше или равно". Т.е., только те события, у которых слот еще не закончился
            events = events.filter(
                status__in=["planned", "started"],
                slots__end_datetime__gte=current_datetime,
            ).annotate(
                # annotate(...) добавляет к каждому событию вычисляемое поле прямо на уровне SQL-запроса.
                # Сортируем список не по "самому первому слоту события в истории", а по ближайшему
                # еще актуальному слоту, который реально должен быть показан клиенту на экране "Запланированные"
                first_slot_start=Min(
                    "slots__start_datetime",
                    filter=Q(slots__status__in=["planned", "started"]),
                )
            )

        # ШАГ 3: Подгружаем к событиям связанные данные из других моделей
        events = (
            # prefetch_related(...) заранее подгружает связанные данные отдельными SQL-запросами,
            # чтобы потом в цикле по событиям не делать N дополнительных запросов к БД (исключаем проблему N+1)
            events.prefetch_related(
                # Prefetch для slots нужен, чтобы:
                #   - получить все слоты события одним набором;
                #   - сразу отсортировать их по start_datetime;
                #   - потом безопасно выбрать display-slot события уже в Python-коде без дополнительных запросов.
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
            # Для фильтра по конкретному дню показываем встречи в естественном порядке времени.
            # Для активных встреч тоже выводим ближайшие сверху.
            # Для архива - наоборот, самые свежие завершенные встречи сверху
            .order_by(
                "first_slot_start" if selected_calendar_day or not show_completed else "-first_slot_start",
                "created_at" if selected_calendar_day or not show_completed else "-created_at",
            )
        )

        # ШАГ 4: Формируем итоговый контракт для HTML
        client_events = []

        # Это локальный in-memory cache на время выполнения одного request.
        # Например:
        #   - у клиента 3 встречи;
        #   - 2 из них с психологом Анной;
        #   - 1 с психологом Олегом.
        # Чтоб не считать для Анны индикатор 2 раза использую specialist_indicator_cache = {}
        specialist_indicator_cache = {}

        # Берем id только что созданной встречи из session и сразу удаляем его оттуда.
        # Это нужно для одноразовой подсветки:
        #   - после redirect клиент видит список своих сессий;
        #   - одна из них только что была создана на предыдущем шаге;
        #   - именно ее мы помечаем как "Только что создано", а при следующем открытии страницы или обновлении
        #   эта подсветка исчезнет, т.е., разово показываем только при создании
        last_created_booking_id = self.request.session.pop("last_created_booking_id", None)

        for event in events:
            # 1) Конкретный календарный день указанный в виджете календаря: активные и уже завершенные
            if selected_calendar_day:
                # В режиме "конкретный день" ищем не абстрактный active/completed slot,
                # а тот слот, который после перевода в timezone клиента попадает именно в выбранную дату.
                # Это важно, потому что встреча может пересекать полночь, а клиенту нужно видеть
                # результат фильтра ровно в своем часовом поясе
                selected_day_slots = [
                    event_slot
                    for event_slot in event.slots.all()
                    if build_calendar_slot_time_display(
                        slot=event_slot,
                        client_timezone=client_timezone,
                    ).get("display_day_key") == selected_calendar_day.isoformat()
                ]
                slot = next(iter(selected_day_slots), None)
            # 2) Для показа всех АРХИВНЫХ событий
            else:
                slot = (
                    get_event_completed_slot(event)
                    if show_completed
                    else get_event_active_slot(event)
                )
            # 3) Для показа всех ЗАПЛАНИРОВАННЫХ событий
            if slot is None and show_completed and not selected_calendar_day:
                fallback_completed_slots = [
                    event_slot
                    for event_slot in event.slots.all()
                    if event_slot.end_datetime < current_datetime
                ]
                slot = next(iter(reversed(fallback_completed_slots)), None)

            # Если по данным события не найдено ни одного подходящего слота, то карточку лучше вообще не выводить
            # на экран календаря
            if slot is None:
                continue

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
            specialist_profile_id = getattr(specialist_profile, "pk", None)
            if specialist_profile_id not in specialist_indicator_cache:
                # Для списка встреч считаем specialist_indicator по каждому специалисту только один раз,
                # даже если у клиента с ним несколько событий в выборке.
                specialist_indicator_cache[specialist_profile_id] = build_specialist_live_indicator(
                    specialist_profile=specialist_profile,
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
                    slot=slot,
                    client_timezone=client_timezone,
                )
                if slot
                else {}
            )
            recurrence_rule = next(iter(event.recurrences.all()), None)

            # Формируем готовую структуру для HTML-шаблона
            client_events.append(
                {
                    "event": event,
                    "slot": slot,
                    "counterpart_user": counterpart_user,
                    "counterpart_full_name": counterpart_full_name or "Имя не указано",
                    "specialist_profile": specialist_profile,
                    "specialist_live_indicator": specialist_indicator_cache[specialist_profile_id],
                    "specialist_photo_url": (
                        counterpart_user.avatar_url
                        if counterpart_user
                        else "/static/images/menu/user-circle.svg"
                    ),
                    "visibility_display": event.get_visibility_display() or "Приватная",
                    "event_type_display": event.get_event_type_display() or "Индивидуальная сессия",
                    "status_display": event.get_status_display() or "Запланировано",
                    "duration_minutes": (
                        int((slot.end_datetime - slot.start_datetime).total_seconds() // 60)
                        if slot
                        else None
                    ),
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
                    "is_recently_created": str(event.id) == last_created_booking_id,
                    # Для day-filter и архивного режима карточка может оказаться "серой",
                    # даже если вся страница открыта не в режиме архива:
                    # например, клиент выбрал день, где есть уже завершенная встреча
                    "is_archived_card": (
                        show_completed
                        or slot.status == "completed"
                        or slot.end_datetime < current_datetime
                    ),
                }
            )

        return client_events

    def _build_calendar_month_widget_events(self) -> list[dict]:
        """Готовит компактный JSON-совместимый набор событий для month-виджета календаря.

        Бизнес-смысл:
            - виджет справа не должен пересчитывать доменную логику;
            - он получает уже готовые даты встреч клиента и только визуально показывает, в какие дни сколько
              активных и сколько уже завершенных сессий есть у клиента;
            - дополнительно этот набор данных нужен JS не только для badge, но и для клика по дню, чтобы
              страница могла переключиться в режим "события выбранного дня".
        """
        current_datetime = timezone.now()
        calendar_events = []
        events = (
            CalendarEvent.objects.filter(
                participants__user=self.request.user,
            )
            .annotate(
                latest_slot_end=Max("slots__end_datetime"),
            )
            .filter(
                Q(status__in=["planned", "started", "completed"])
                | Q(latest_slot_end__lt=current_datetime)
            )
            .prefetch_related(
                Prefetch("slots", queryset=TimeSlot.objects.order_by("start_datetime")),
            )
            .distinct()
        )

        for event in events:
            # Для календарного виджета нужно различать два типа счетчиков:
            #   - активные встречи;
            #   - завершенные встречи.
            # Поэтому заранее определяем "бакет" события и выбираем слот, который будет отвечать за дату на календаре
            is_completed_bucket = (
                event.status == "completed"
                or (
                    getattr(event, "latest_slot_end", None) is not None
                    and event.latest_slot_end < current_datetime
                )
            )
            slot = (
                get_event_completed_slot(event)
                if is_completed_bucket
                else get_event_active_slot(event)
            )
            if slot is None and is_completed_bucket:
                fallback_completed_slots = [
                    event_slot
                    for event_slot in event.slots.all()
                    if event_slot.end_datetime < current_datetime
                ]
                slot = next(iter(reversed(fallback_completed_slots)), None)
            if slot is None:
                continue
            slot_display_data = build_calendar_slot_time_display(
                slot=slot,
                client_timezone=getattr(self.request.user, "timezone", None),
            )

            # Формируем минимальный набор данных, который нужен именно JS-календарю.
            # То есть month-виджет не получает всю карточку встречи, а только то, что нужно ему
            calendar_events.append(
                {
                    "id": str(event.id),
                    "title": event.title,
                    "start": slot_display_data.get("display_start_iso"),  # нужен для календарного виджета FullCalendar
                    "end": slot_display_data.get("display_end_iso"),  # нужен для календарного виджета FullCalendar
                    "status": event.status,
                    "day_key": slot_display_data.get("display_day_key"),  # нужен для счетчика встреч по дням
                    "bucket": "completed" if is_completed_bucket else "active",
                }
            )

        return calendar_events
