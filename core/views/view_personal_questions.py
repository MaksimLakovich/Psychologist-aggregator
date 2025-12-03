from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, TemplateView


class ClientPersonalQuestionsPageView(LoginRequiredMixin, TemplateView):
    """Контроллер на основе FormView для отображения страницы *Персональные вопросы*."""

    template_name = "core/client_pages/home_client_personal_questions.html"

    # def get_context_data(self, **kwargs):
    #     """Формирование контекста для передачи данных в HTML-шаблон.
    #     1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
    #     пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
    #     2) Возвращает:
    #         - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
    #     context = super().get_context_data(**kwargs)
    #     context["title_home_page_view"] = "Психологи онлайн на Опора — поиск и подбор психолога"
    #
    #     return context
