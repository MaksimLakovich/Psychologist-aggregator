from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView

from core.forms.form_choice_psychologist import ClientChoicePsychologistForm


class ClientChoicePsychologistPageView(LoginRequiredMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Выбор психолога*."""

    template_name = "core/client_pages/home_client_choice_psychologist.html"
    form_class = ClientChoicePsychologistForm
    success_url = reverse_lazy("core:payment-card")

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в HTML-шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) Возвращает:
        - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)

        # Если это новая повторная фильтрация/подбор - то сбрасываем выбор психолога на странице.
        # Понимание, что это новая фильтрация мы получаем в "reset_choice_psychologist" из view_personal_questions.py
        context["reset_choice_psychologist"] = self.request.session.pop(
            "reset_choice_psychologist",
            False,
        )

        context["title_home_page_view"] = "Психологи онлайн на Опора — поиск и подбор психолога"

        return context
