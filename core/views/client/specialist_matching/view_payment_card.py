from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import FormView

from core.forms.client.specialist_matching.form_payment_card import \
    ClientAddPaymentCardForm
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin


class ClientAddPaymentCardPageView(SpecialistMatchingLayoutMixin, LoginRequiredMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Завершение записи и добавление платежной карты*."""

    template_name = "core/client_pages/specialist_matching/home_client_payment_card.html"
    form_class = ClientAddPaymentCardForm

    def get_success_url(self):
        """Пока остаемся на этом шаге, но сохраняем layout и после submit."""
        return f"{reverse('core:payment-card')}{self._build_layout_query()}"  # TODO: Заменить позже, когда создам след страницу

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
