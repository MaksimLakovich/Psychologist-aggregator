from django.views.generic import TemplateView


class CommonQuestionPageView(TemplateView):
    """Класс-контроллер на основе Generic для отображения страницы *ВОПРОСЫ-ОТВЕТЫ*."""

    template_name = "core/client_pages/my_account/questions_answers.html"

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) В текущей реализации передаем:
            - Заголовок страницы (title)
            - Параметр для настройки отображения меню/навигация (sidebar / without-sidebar)
            - Параметр для подсветки выбранного пункта в навигации
        3) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["title_common_question_page_view"] = "Вопросы и ответы — Опора"

        # Логика управление отображением сайдбара:
        # 1) если пришли из сайдбара, показываем его;
        # 2) и показываем верхнее меню без сайдбара, если открыли не из сайдбара
        from_sidebar = self.request.GET.get("layout") == "sidebar"
        context["show_sidebar"] = from_sidebar

        if not from_sidebar:
            context["menu_variant"] = "without-sidebar"

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "faq"

        return context
