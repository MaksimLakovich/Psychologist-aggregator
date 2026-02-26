from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import FormView

from core.forms.client.specialist_matching.form_general_questions import \
    ClientGeneralQuestionsForm
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin


class ClientGeneralQuestionsPageView(SpecialistMatchingLayoutMixin, LoginRequiredMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Общие вопросы*."""

    template_name = "core/client_pages/specialist_matching/home_client_general_questions.html"
    form_class = ClientGeneralQuestionsForm

    def get_initial(self):
        """Возвращает предзаполненные значения формы, полученные из AppUser и ClientProfile.
        Вызывается автоматически FormView при создании формы."""
        user = self.request.user
        profile = user.client_profile

        return {
            "first_name": user.first_name,
            "email": user.email,  # просто показываем, так как в форме (disabled=True)
            "age": user.age,
            "timezone": user.timezone or None,
            "therapy_experience": profile.therapy_experience,
        }

    def form_valid(self, form):
        """Вызывается автоматически при успешной валидации POST-запроса.
        Логика сохранения находится внутри формы в методе save()."""
        form.save(self.request.user)

        return super().form_valid(form)

    def get_success_url(self):
        """Формирует URL следующего шага с сохранением текущего layout."""
        return f"{reverse('core:personal-questions')}{self._build_layout_query()}"

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в HTML-шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["title_home_page_view"] = "Психологи онлайн на Опора — поиск и подбор психолога"

        # Логика управление отображением сайдбара:
        # 1) если пришли из сайдбара, показываем его;
        # 2) и показываем верхнее меню без сайдбара, если открыли не из сайдбара
        self._apply_layout_context(context)

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "psychologist-match"

        return context
