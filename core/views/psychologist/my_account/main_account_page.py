from django.views.generic import TemplateView

from users.mixins.role_required_mixin import PsychologistRequiredMixin


class PsychologistAccountView(PsychologistRequiredMixin, TemplateView):
    """Класс-контроллер на основе Generic для отображения *Кабинета специалиста*.

    - Используется как точка для работы с профилем (редактирование) и работы с функционалом платформы (поиск
      специалистов, работа с календарем, работа с событиями и их проведением (комнаты), уведомления, чат и др.
    - HTML-шаблон получает данные через контекст (title), чтобы гибко управлять контентом в интерфейсе."""

    template_name = "core/psychologist_pages/my_account/main_account.html"

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) В текущей реализации передаем:
            - Заголовок страницы (title)
            - Параметр для настройки отображения меню/навигация
            - Параметр для подсветки выбранного пункта в навигации
        3) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)

        context["title_psychologist_account_view"] = "Кабинет специалиста в сервисе ОПОРА"

        # Параметр, который передаем в menu.html и на его основе там настраиваем показ САЙДБАРА
        context["show_sidebar"] = "sidebar"

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "psychologist-account"

        return context
