from django.urls import reverse
from django.views.generic import FormView

from core.forms.client.specialist_matching.form_choice_psychologist import ClientChoicePsychologistForm
from core.services.get_client_timezone_value import get_client_timezone_value_for_request
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin


class ClientChoicePsychologistPageView(SpecialistMatchingLayoutMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Выбор психолога*.

    Вью работает в двух сценариях:
        - сценарий 1: работает зарегистрированный авторизованный пользователь;
        - сценарий 2: работает guest-anonymous.
    """

    template_name = "core/client_pages/specialist_matching/home_client_choice_psychologist.html"
    form_class = ClientChoicePsychologistForm

    def get_success_url(self):
        """Формирует URL следующего шага с сохранением текущего layout."""
        return f"{reverse('core:payment-card')}{self._build_layout_query()}"

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в HTML-шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) Возвращает:
        - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)

        # Если это новая повторная фильтрация/подбор - то сбрасываем выбор психолога на странице.
        # Понимание, что это новая фильтрация мы получаем в "reset_choice_psychologist" из view_personal_questions.py
        # 1) сброс при нажатии кнопки "ДАЛЕЕ" внизу страницы (базовый пользовательский сценарий)
        reset_from_session = self.request.session.pop(
            "reset_choice_psychologist",
            False,
        )
        # 2) сброс при выборе следующего ШАГА в дорожно карте (доп сценарий)
        reset_from_query = self.request.GET.get("reset") == "1"

        context["reset_choice_psychologist"] = (
            reset_from_session or reset_from_query
        )

        context["title_home_page_view"] = "Психологи онлайн на Опора — поиск и подбор психолога"

        # get_client_timezone_value_for_request() - возвращает TZ текущего участника flow в строковом виде:
        # - для авторизованного клиента timezone берется из аккаунта;
        # - для гостя из временного guest-anonymous-состояния в session, собранного на первом шаге подбора
        context["client_timezone_value"] = get_client_timezone_value_for_request(self.request)

        # Логика управление отображением сайдбара:
        # 1) если пришли из сайдбара, показываем его;
        # 2) и показываем верхнее меню без сайдбара, если открыли не из сайдбара
        self._apply_layout_context(context)

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "psychologist-match"

        return context
