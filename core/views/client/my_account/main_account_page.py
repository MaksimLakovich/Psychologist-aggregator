from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from core.services.topic_groups import build_topics_grouped_by_type
from core.views.client.my_account.events_page import \
    load_client_next_planned_event_data
from users.models import ClientProfile, Method


class ClientAccountView(LoginRequiredMixin, TemplateView):
    """Класс-контроллер на основе Generic для отображения *Кабинета клиента*.

    - Используется как точка для работы с профилем (редактирование) и работы с функционалом платформы (поиск
      подходящего специалиста, запись, работа с бронированием сессий и их проведением (комнаты), уведомления, чат и др.
    - HTML-шаблон получает данные через контекст (title), чтобы гибко управлять контентом в интерфейсе.
    """

    template_name = "core/client_pages/my_account/main_account.html"

    def _get_my_therapist_data(self, upcoming_event_data) -> dict:
        """Возвращает данные для блока "Мой терапевт" на главной странице кабинета клиента.

        Бизнес-смысл:
            - в текущей модели у клиента нет отдельного закрепления постоянного "мой терапевт";
            - поэтому источником истины сейчас является ближайшая запланированная терапевтическая встреча;
            - если запланированных встреч пока нет, блок отрисовывается заглушкой, но без ошибки.
        """
        if upcoming_event_data is None:
            return {
                "therapist_full_name": "Терапевт не назначен",
                "therapist_photo_url": "/static/images/menu/user-circle.svg",
                "therapist_subtitle": "Специалист появится после записи на встречу",
                "therapist_live_indicator": {
                    "title": "Специалист пока не назначен",
                    "label": "Терапевт появится после записи",
                    "dot_color": "#d4d4d8",
                    "ping_color": "#d4d4d8",
                    "should_ping": False,
                },
                "specialist_profile_url": None,
            }

        specialist_profile = upcoming_event_data["specialist_profile"]

        return {
            "therapist_full_name": upcoming_event_data["counterpart_full_name"] or "Имя не указано",
            "therapist_photo_url": upcoming_event_data["specialist_photo_url"],
            "therapist_subtitle": (
                f"Психолог • {specialist_profile.get_therapy_format_display()}"
                if specialist_profile
                else "Психолог"
            ),
            "therapist_live_indicator": upcoming_event_data["specialist_live_indicator"],
            "specialist_profile_url": upcoming_event_data["specialist_profile_url"],
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
        upcoming_event_data = load_client_next_planned_event_data(
            user=self.request.user,
            viewer_timezone=getattr(self.request.user, "timezone", None),
            detail_layout="sidebar",
        )

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

        # Блок "Мой терапевт" / Или заглушка, если нет встреч запланированных ни с кем
        context.update(self._get_my_therapist_data(upcoming_event_data))

        return context
