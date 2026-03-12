from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Min, Prefetch
from django.utils import timezone
from django.views.generic import TemplateView

from calendar_engine.models import CalendarEvent, EventParticipant, TimeSlot
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin


class ClientPlannedSessionsView(SpecialistMatchingLayoutMixin, LoginRequiredMixin, TemplateView):
    """Контроллер страницы *Мой кабинет / Календарь сессий / Запланированные*.

    Бизнес-смысл страницы:
        - после успешного создания терапевтической сессии клиент должен сразу увидеть, что встреча действительно
          создана;
        - экран показывает будущие встречи клиента со статусом planned, а также уже начавшиеся встречи со
          статусом started, чтобы клиент не потерял к ним быстрый доступ;
        - layout страницы должен сохраняться в том же режиме (верхнее меню или сайдбар), из которого клиент прошел
          шаги подбора и записи.
    """

    template_name = "core/client_pages/my_account/planned_sessions.html"

    def _build_planned_events(self):
        """Собирает удобную для шаблона проекцию запланированных и уже начавшихся сессий клиента."""
        upcoming_events = (
            CalendarEvent.objects.filter(
                participants__user=self.request.user,
                status__in=["planned", "started"],
                slots__end_datetime__gte=timezone.now(),
            )
            .annotate(first_slot_start=Min("slots__start_datetime"))
            .prefetch_related(
                Prefetch("slots", queryset=TimeSlot.objects.order_by("start_datetime")),
                Prefetch(
                    "participants",
                    queryset=EventParticipant.objects.select_related("user").order_by("pk"),
                ),
            )
            .distinct()
            .order_by("first_slot_start", "created_at")
        )

        planned_events = []
        # Берем id только что созданной встречи из session и сразу удаляем его оттуда.
        # Это нужно для одноразовой подсветки:
        #   - после redirect клиент видит список своих сессий;
        #   - одна из них только что была создана на предыдущем шаге;
        #   - именно ее мы помечаем как "Только что создано", а при следующем открытии страницы эта подсветка уже
        #     не должна повторяться бесконечно.
        last_created_booking_id = self.request.session.pop("last_created_booking_id", None)

        for event in upcoming_events:
            # Берем первый слот встречи как основной слот для карточки списка.
            # На текущем этапе у нас создается одна терапевтическая сессия = один TimeSlot,
            # но код сразу написан так, чтобы экран не ломался, если позже в событии появится несколько слотов.
            primary_slot = next(iter(event.slots.all()), None)

            # Находим второго участника встречи, чтобы показать клиенту с кем именно у него назначена сессия.
            counterpart_participant = next(
                (
                    participant
                    for participant in event.participants.all()
                    if participant.user_id != self.request.user.pk
                ),
                None,
            )

            planned_events.append(
                {
                    "event": event,
                    "primary_slot": primary_slot,
                    "counterpart_user": counterpart_participant.user if counterpart_participant else None,
                    "is_recently_created": str(event.id) == last_created_booking_id,
                }
            )

        return planned_events

    def get_context_data(self, **kwargs):
        """Формирует контекст страницы запланированных сессий клиента."""
        context = super().get_context_data(**kwargs)
        context["title_client_account_view"] = "Запланированные сессии на ОПОРА"

        # Применяем тот же layout-режим, который сопровождал клиента на шагах подбора и записи:
        # либо верхнее меню, либо сайдбар.
        self._apply_layout_context(context)

        context["current_sidebar_key"] = "session-planned"
        context["planned_events"] = self._build_planned_events()
        return context
