from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Min, Prefetch
from django.utils import timezone
from django.views.generic import TemplateView

from calendar_engine.booking.services import build_specialist_live_indicator
from calendar_engine.lifecycle.event_status_lifecycle import \
    apply_time_based_status_transitions_for_user
from calendar_engine.models import CalendarEvent, EventParticipant, TimeSlot


class ClientAccountView(LoginRequiredMixin, TemplateView):
    """Класс-контроллер на основе Generic для отображения *Кабинета клиента*.

    - Используется как точка для работы с профилем (редактирование) и работы с функционалом платформы (поиск
      подходящего специалиста, запись, работа с бронированием сессий и их проведением (комнаты), уведомления, чат и др.
    - HTML-шаблон получает данные через контекст (title), чтобы гибко управлять контентом в интерфейсе.
    """

    template_name = "core/client_pages/my_account/main_account.html"

    def _get_my_therapist_data(self) -> dict:
        """Возвращает данные для блока "Мой терапевт" на главной странице кабинета клиента.

        Бизнес-смысл:
            - в текущей модели у клиента нет отдельного закрепления постоянного "мой терапевт";
            - поэтому источником истины сейчас является ближайшая запланированная терапевтическая встреча;
            - если запланированных встреч пока нет, блок отрисовывается заглушкой, но без ошибки.
        """
        # Запуск автоматического обновления/определения статусов event/slot по фактическому времени
        apply_time_based_status_transitions_for_user(participant_user=self.request.user)
        events = (
            CalendarEvent.objects.filter(
                participants__user=self.request.user,
                status__in=["planned", "started"],
                slots__end_datetime__gte=timezone.now(),
            )
            .annotate(first_slot_start=Min("slots__start_datetime"))
            .prefetch_related(
                Prefetch(
                    "participants",
                    queryset=EventParticipant.objects.select_related(
                        "user",
                        "user__psychologist_profile",
                    ).order_by("pk"),
                ),
                Prefetch("slots", queryset=TimeSlot.objects.order_by("start_datetime")),
            )
            .distinct()
            .order_by("first_slot_start", "created_at")
            .first()
        )

        if events is None:
            return {
                "therapist_full_name": "Терапевт не назначен",
                "therapist_photo_url": "/static/images/menu/user-circle.svg",
                "therapist_subtitle": "Специалист появится после записи на встречу",
                "therapist_live_indicator": build_specialist_live_indicator(specialist_profile=None),
            }

        counterpart_participant = next(
            (
                participant
                for participant in events.participants.all()
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
        therapist_full_name = (
            f"{counterpart_user.first_name} {counterpart_user.last_name}".strip()
            if counterpart_user
            else ""
        )

        return {
            "therapist_full_name": therapist_full_name or "Имя не указано",
            "therapist_photo_url": (
                counterpart_user.avatar_url
                if counterpart_user
                else "/static/images/menu/user-circle.svg"
            ),
            "therapist_subtitle": (
                f"Психолог • {specialist_profile.get_therapy_format_display()}"
                if specialist_profile
                else "Психолог"
            ),
            "therapist_live_indicator": build_specialist_live_indicator(
                specialist_profile=specialist_profile,
            ),
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

        # Блок "Мой терапевт" / Или заглушка, если нет встреч запланированных ни с кем
        context.update(self._get_my_therapist_data())

        return context
