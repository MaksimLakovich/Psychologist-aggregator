from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView
from core.forms.form_general_questions import ClientGeneralQuestionsForm


class ClientGeneralQuestionsPageView(LoginRequiredMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Общие вопросы*."""

    template_name = "core/client_pages/home_client_general_questions.html"
    form_class = ClientGeneralQuestionsForm
    success_url = reverse_lazy("core:client_personal_questions_page")

    def get_initial(self):
        """Возвращает предзаполненные значения формы, полученные из AppUser и ClientProfile.
        Вызывается автоматически FormView при создании формы."""
        user = self.request.user
        profile = user.client_profile

        return {
            "first_name": user.first_name,
            "email": user.email,  # просто показываем, так как в форме (disabled=True)
            "age": user.age,
            "timezone": user.timezone,
            "therapy_experience": profile.therapy_experience,
        }

    def form_valid(self, form):
        """Вызывается автоматически при успешной валидации POST-запроса.
        Логика сохранения находится внутри формы в методе save()."""
        form.save(self.request.user)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в HTML-шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["title_home_page_view"] = "Психологи онлайн на Опора — поиск и подбор психолога"

        return context
