from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from core.forms.form_personal_questions import ClientPersonalQuestionsForm
from users.models import ClientProfile, Method


class ClientPersonalQuestionsPageView(LoginRequiredMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Персональные вопросы* - предпочтения клиента."""

    template_name = "core/client_pages/home_client_personal_questions.html"
    form_class = ClientPersonalQuestionsForm
    success_url = reverse_lazy("core:client_personal_questions_page")  # TODO: заменить позже

    def get_initial(self):
        """Возвращает предзаполненные значения формы, полученные из ClientProfile по данным:
            - has_preferences;
            - preferred_methods.
        Вызывается автоматически FormView при создании формы."""
        initial = super().get_initial()

        user = self.request.user
        profile = get_object_or_404(ClientProfile, user=user)

        # has_preferences
        initial["has_preferences"] = profile.has_preferences

        # preferred_methods
        try:
            selected = profile.preferred_methods.values_list("id", flat=True)
            initial["preferred_methods"] = list(selected)
        except Exception:
            initial["preferred_methods"] = []

        return initial

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в HTML-шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) Возвращает:
        - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["methods"] = Method.objects.all().order_by("name")

        form = context["form"]

        # Для шаблона: превращаем PK методов в строки (чтобы удобнее работать в JS)
        context["selected_methods"] = [
            str(pk) for pk in form.initial.get("preferred_methods", [])
        ]

        # Новое: пробрасываем has_preferences в шаблон
        context["has_preferences"] = form.initial.get("has_preferences", False)

        context["title_home_page_view"] = "Психологи онлайн на Опора — поиск и подбор психолога"

        return context

    def form_valid(self, form):
        """Сохраняем изменения в профиле (fallback-сохранение, если AJAX не сработал)."""
        client_profile = get_object_or_404(ClientProfile, user=self.request.user)

        # 1. Сохраняем has_preferences
        client_profile.has_preferences = form.cleaned_data.get("has_preferences", False)

        # 2. Сохраняем preferred_methods
        selected_methods = form.cleaned_data["preferred_methods"]
        client_profile.preferred_methods.set(selected_methods)

        client_profile.save()

        return super().form_valid(form)
