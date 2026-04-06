from django.views.generic import TemplateView

from users.mixins.role_required_mixin import ClientRequiredMixin


class StartPageView(ClientRequiredMixin, TemplateView):
    """Класс-контроллер на основе Generic для отображения *Стартовой страницы сайта*.
    1) Используется как стартовая точка только для гостя и клиента - здесь размещается базовая информация о проекте,
    поиск психолога и клиентские CTA.
    2) HTML-шаблон получает данные через контекст (title / header / description), чтобы гибко управлять контентом
    в интерфейсе."""

    template_name = "core/start_page.html"
    allow_anonymous = True  # страницу можно открыть не только клиенту, но и вообще гостю без логина

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) В текущей реализации передаем:
            - Заголовок страницы (title)
            - Оглавление основного блока
            - Описание
        3) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["title_start_page_view"] = "Психологи онлайн на Опора — поиск и подбор психолога"
        context["header_start_page_view"] = "Найдите подходящего психолога онлайн"
        context["description_start_page_view"] = (
            "Мы помогаем подобрать квалифицированного психолога для ваших запросов — конфиденциально, "
            "быстро и удобно. Только проверенные специалисты с подтверждённым опытом."
        )

        return context
