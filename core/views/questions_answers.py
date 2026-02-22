from django.views.generic import TemplateView


class CommonQuestionPageView(TemplateView):
    """Класс-контроллер на основе Generic для отображения страницы *ВОПРОСЫ-ОТВЕТЫ*."""

    template_name = "core/questions_answers.html"

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) В текущей реализации передаем:
            - Заголовок страницы (title)
        3) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["title_common_question_page_view"] = "Вопросы и ответы — Опора"

        # Параметр, который передаем в menu.html и на его основе там настраиваем показ боков.НАВИГАЦИЙ / верх.МЕНЮ
        # Данный IF/ELSE позволяет нам задать отдельный параметр для клиента и для психолога, что позволит потом,
        # при необходимости, рендерить разные шаблоны страниц или использовать разный доп функционал
        if getattr(self.request.user, "role_id", None) == 2:
            context["profile_type"] = "client"
        else:
            context["profile_type"] = "psychologist"

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "faq"

        return context
