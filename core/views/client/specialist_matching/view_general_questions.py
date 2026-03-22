from django.urls import reverse
from django.views.generic import FormView

from core.forms.client.specialist_matching.form_general_questions import ClientGeneralQuestionsForm
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin
from core.services.anonymous_client_flow_for_search_and_booking import get_guest_matching_state, update_guest_general_state


class ClientGeneralQuestionsPageView(SpecialistMatchingLayoutMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Общие вопросы*.

    Вью работает в двух сценариях:
        - сценарий 1: работает зарегистрированный авторизованный пользователь;
        - сценарий 2: работает guest-anonymous.
    """

    template_name = "core/client_pages/specialist_matching/home_client_general_questions.html"
    form_class = ClientGeneralQuestionsForm

    def get_form_kwargs(self):
        """Передает в форму режим работы поля email для двух сценариев.

        Форма сама не знает, кто сейчас проходит шаг:
            - сценарий 1: авторизованный клиент;
            - сценарий 2: guest-anonymous.

        Поэтому здесь явно передаем флаг email_readonly, чтобы форма:
            - оставляла email read-only для авторизованного клиента;
            - делала email редактируемым для гостя.
        """
        kwargs = super().get_form_kwargs()
        kwargs["email_readonly"] = self.request.user.is_authenticated
        return kwargs

    def get_initial(self):
        """Возвращает initial-значения формы для двух сценариев шага "Общие вопросы"."""
        # Сценарий 1: Авторизованный клиент. Берем данные из реальных моделей AppUser и ClientProfile
        if self.request.user.is_authenticated:
            user = self.request.user
            profile = user.client_profile

            return {
                "first_name": user.first_name,
                "email": user.email,  # просто показываем, так как в форме (disabled=True)
                "age": user.age,
                "timezone": user.timezone or None,
                "therapy_experience": profile.therapy_experience,
            }

        # Сценарий 2: Guest-anonymous.
        # Берем ранее сохраненный черновик из session и явно приводим его к формату initial для формы.
        # Здесь лучше вернуть явный словарь, а не просто "return get_guest_matching_state()":
        #   - timezone для пустого значения должен стать None, а не пустой строкой;
        #   - форма получает только те поля, которые реально ожидает;
        #   - код остается устойчивым, даже если в session позже появятся дополнительные служебные ключи
        general = get_guest_matching_state(self.request.session)["general"]
        return {
            "first_name": general.get("first_name", ""),
            "email": general.get("email", ""),
            "age": general.get("age"),
            "timezone": general.get("timezone") or None,
            "therapy_experience": general.get("therapy_experience", False),
        }

    def form_valid(self, form):
        """Сохраняет шаг "Общие вопросы" для двух сценариев."""
        # Сценарий 1: Авторизованный клиент. Сохраняем данные в реальные модели пользователя
        if self.request.user.is_authenticated:
            form.save(self.request.user)
        else:
            # 2) Сценарий 2: Guest-anonymous. Сохраняем ответы гостя во временный session-state до регистрации
            update_guest_general_state(
                self.request.session,
                payload={
                    "first_name": form.cleaned_data.get("first_name", "") or "",
                    "email": form.cleaned_data.get("email", "") or "",
                    "age": form.cleaned_data.get("age"),
                    "timezone": str(form.cleaned_data.get("timezone") or ""),
                    "therapy_experience": bool(form.cleaned_data.get("therapy_experience", False)),
                },
            )

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
