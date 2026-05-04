from django.db.models import Min, Prefetch, Q
from django.utils import timezone
from django.views.generic import TemplateView

from calendar_engine.lifecycle.use_cases.apply_time_based_status_transitions import \
    apply_time_based_status_transitions_for_user
from calendar_engine.models import CalendarEvent, EventParticipant, TimeSlot
from core.services.calendar_adapters.ps_event_adapters import \
    build_psychologist_event_card
from core.services.calendar_event_slot_selector import get_event_active_slot
from users.mixins.role_required_mixin import PsychologistRequiredMixin


class PsychologistAccountView(PsychologistRequiredMixin, TemplateView):
    """Класс-контроллер на основе Generic для отображения *Кабинета специалиста*.

    - Используется как точка для работы с профилем (редактирование) и работы с функционалом платформы (поиск
      специалистов, работа с календарем, работа с событиями и их проведением (комнаты), уведомления, чат и др.
    - HTML-шаблон получает данные через контекст (title), чтобы гибко управлять контентом в интерфейсе.
    """

    template_name = "core/psychologist_pages/my_account/main_account.html"

    def _get_upcoming_event_cards(self) -> list[dict]:
        """Собирает данные ближайших активных встреч для главной страницы кабинета специалиста."""
        apply_time_based_status_transitions_for_user(participant_user=self.request.user)
        current_datetime = timezone.now()
        viewer_timezone = getattr(self.request.user, "timezone", None)
        layout_query = "?layout=sidebar"

        events = (
            CalendarEvent.objects.filter(
                participants__user=self.request.user,
                status__in=["planned", "started"],
                slots__end_datetime__gte=current_datetime,
            )
            .annotate(
                first_slot_start=Min(
                    "slots__start_datetime",
                    filter=Q(
                        slots__status__in=["planned", "started"],
                        slots__end_datetime__gte=current_datetime,
                    ),
                )
            )
            .prefetch_related(
                Prefetch("slots", queryset=TimeSlot.objects.order_by("start_datetime")),
                Prefetch("recurrences"),
                Prefetch(
                    "participants",
                    queryset=EventParticipant.objects.select_related(
                        "user",
                        "user__psychologist_profile",
                    ).order_by("pk"),
                ),
            )
            .distinct()
            .order_by("first_slot_start", "created_at")[:5]
        )

        event_cards = []

        for event in events:
            slot = get_event_active_slot(event)
            if slot is None:
                continue

            card = build_psychologist_event_card(
                event=event,
                slot=slot,
                viewer_user=self.request.user,
                viewer_timezone=viewer_timezone,
                current_datetime=current_datetime,
                layout_query=layout_query,
            )
            card["description"] = event.description
            event_cards.append(card)

        return event_cards

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) В текущей реализации передаем:
            - Заголовок страницы (title)
            - Параметр для настройки отображения меню/навигация
            - Параметр для подсветки выбранного пункта в навигации
        3) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["title_psychologist_account_view"] = "Кабинет специалиста в сервисе ОПОРА"

        # Параметр, который передаем в menu.html и на его основе там настраиваем показ САЙДБАРА
        context["show_sidebar"] = "sidebar"

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "psychologist-account"

        upcoming_events = self._get_upcoming_event_cards()

        context["upcoming_events"] = upcoming_events
        context["upcoming_event"] = next(iter(upcoming_events), None)

        return context
