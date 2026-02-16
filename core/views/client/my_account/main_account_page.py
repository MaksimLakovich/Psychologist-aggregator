from django.views.generic import TemplateView


class ClientAccountView(TemplateView):
    """Класс-контроллер на основе Generic для отображения *Кабинета клиента*.
    1) Используется как точка для работы с профилем (редактирование) и работы с функционалом платформы (поиск
    подходящего специалиста, запись, работа с бронированием сессий и их проведением (комнаты), уведомления, чат и др.
    2) HTML-шаблон получает данные через контекст (title), чтобы гибко управлять контентом в интерфейсе."""

    template_name = "core/client_pages/my_account/main_account.html"

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) В текущей реализации передаем:
            - Заголовок страницы (title)
        3) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["title_client_account_view"] = "Мой кабинет на ОПОРА"
        context["profile_type"] = "client"
        return context
