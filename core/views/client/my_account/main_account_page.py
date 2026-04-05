from django.db.models import Min, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from calendar_engine.booking.services import build_specialist_live_indicator
from calendar_engine.lifecycle.use_cases.apply_time_based_status_transitions import \
    apply_time_based_status_transitions_for_user
from calendar_engine.models import CalendarEvent, EventParticipant, TimeSlot
from core.services.calendar_event_slot_selector import get_event_active_slot
from core.services.calendar_slot_time_display import \
    build_calendar_slot_time_display
from core.services.topic_groups import build_topics_grouped_by_type
from users.mixins.role_required_mixin import ClientRequiredMixin
from users.models import ClientProfile, Method


class ClientAccountView(ClientRequiredMixin, TemplateView):
    """Класс-контроллер на основе Generic для отображения *Кабинета клиента*.

    - Используется как точка для работы с профилем (редактирование) и работы с функционалом платформы (поиск
      подходящего специалиста, запись, работа с бронированием сессий и их проведением (комнаты), уведомления, чат и др.
    - HTML-шаблон получает данные через контекст (title), чтобы гибко управлять контентом в интерфейсе.
    """

    template_name = "core/client_pages/my_account/main_account.html"

    def _get_upcoming_event_data(self) -> dict | None:
        """Собирает данные ближайшей активной встречи именно для главной страницы кабинета клиента."""
        apply_time_based_status_transitions_for_user(participant_user=self.request.user)
        current_datetime = timezone.now()
        client_timezone = getattr(self.request.user, "timezone", None)

        event = (
            CalendarEvent.objects.filter(
                participants__user=self.request.user,
                status__in=["planned", "started"],
                slots__end_datetime__gte=current_datetime,
            )
            .annotate(
                first_slot_start=Min(
                    "slots__start_datetime",
                    filter=Q(slots__status__in=["planned", "started"]),
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
            .order_by("first_slot_start", "created_at")
            .first()
        )

        if event is None:
            return None

        slot = get_event_active_slot(event)
        if slot is None:
            return None

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
        recurrence_rule = next(iter(event.recurrences.all()), None)
        detail_url = reverse(
            "core:client-therapy-session-detail",
            kwargs={"event_id": event.id},
        )
        slot_display_data = build_calendar_slot_time_display(
            slot=slot,
            client_timezone=client_timezone,
        )

        return {
            "slot": slot,
            "description": event.description,
            "counterpart_full_name": (
                f"{counterpart_user.first_name} {counterpart_user.last_name}".strip()
                if counterpart_user
                else "Специалист будет указан позже"
            ),
            "specialist_profile": specialist_profile,
            "specialist_photo_url": (
                counterpart_user.avatar_url
                if counterpart_user
                else "/static/images/menu/user-circle.svg"
            ),
            "specialist_live_indicator": build_specialist_live_indicator(
                specialist_profile=specialist_profile,
            ),
            "event_type_display": event.get_event_type_display() or "Индивидуальная сессия",
            "frequency_display": (
                recurrence_rule.get_frequency_display()
                if recurrence_rule and recurrence_rule.frequency
                else "Разовая встреча"
            ),
            "status_display": slot.get_status_display() or "Запланировано",
            "detail_url": f"{detail_url}?layout=sidebar",
            **slot_display_data,
        }

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
        context["title_client_account_view"] = "Мой кабинет на ОПОРА"

        # Параметр, который передаем в menu.html и на его основе там настраиваем показ САЙДБАРА
        context["show_sidebar"] = "sidebar"

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "client-account"

        client_profile = get_object_or_404(
            ClientProfile.objects.prefetch_related("requested_topics", "preferred_methods"),
            user=self.request.user,
        )
        upcoming_event_data = self._get_upcoming_event_data()

        context["upcoming_event"] = upcoming_event_data
        context["topics_by_type"] = build_topics_grouped_by_type()
        context["selected_topics"] = [
            str(topic_id)
            for topic_id in client_profile.requested_topics.values_list("id", flat=True)
        ]
        context["selected_methods"] = [
            str(method_id)
            for method_id in client_profile.preferred_methods.values_list("id", flat=True)
        ]
        context["client_requested_topics"] = client_profile.requested_topics.all().order_by(
            "type",
            "group_name",
            "name",
        )
        context["client_preferred_methods"] = Method.objects.filter(
            id__in=client_profile.preferred_methods.values_list("id", flat=True)
        ).order_by("name")
        context["all_methods"] = Method.objects.all().order_by("name")

        return context
