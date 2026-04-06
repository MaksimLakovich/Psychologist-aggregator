from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from core.forms.client.specialist_matching.form_choice_psychologist import \
    ClientChoicePsychologistForm
from core.services.get_client_timezone_value import \
    get_client_timezone_value_for_request
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin
from users.mixins.role_required_mixin import ClientRequiredMixin


class ClientChoicePsychologistPageView(ClientRequiredMixin, SpecialistMatchingLayoutMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Выбор психолога*.

    Вью работает в двух сценариях:
        - сценарий 1: работает зарегистрированный авторизованный пользователь;
        - сценарий 2: работает guest-anonymous.
    """

    template_name = "core/client_pages/specialist_matching/home_client_choice_psychologist.html"
    form_class = ClientChoicePsychologistForm
    allow_anonymous = True

    def get(self, request, *args, **kwargs):
        """Одноразово потребляет query-параметр reset=1 и очищает URL страницы.

        Бизнес-смысл:
            - reset=1 нужен только для первого входа после новой фильтрации, чтобы сбросить ранее выбранного
              специалиста и открыть начало новой выдачи;
            - если оставить reset=1 в адресной строке, то каждое обновление браузера будет снова сбрасывать выбор
              клиента на первого специалиста, что ломает UX.

        Поэтому:
            1) переносим reset в session как одноразовый флаг;
            2) сразу редиректим на тот же URL, но уже без reset.
        """
        if request.GET.get("reset") == "1":
            request.session["reset_choice_psychologist"] = True

            clean_query_params = request.GET.copy()
            clean_query_params.pop("reset", None)
            clean_query = clean_query_params.urlencode()
            clean_url = request.path if not clean_query else f"{request.path}?{clean_query}"

            return redirect(clean_url)

        return super().get(request, *args, **kwargs)

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
        # 1) reset_choice_psychologist хранится в session как одноразовый флаг.
        # Он включается:
        #   - после новой фильтрации на предыдущем шаге;
        #   - или при первом входе по URL с reset=1, который мы сразу очищаем в методе get().
        # После чтения флаг удаляется, чтобы refresh страницы больше не сбрасывал выбор специалиста.
        context["reset_choice_psychologist"] = self.request.session.pop(
            "reset_choice_psychologist",
            False,
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
