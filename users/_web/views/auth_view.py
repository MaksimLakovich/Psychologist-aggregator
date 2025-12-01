from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from users._web.forms.auth_form import AppUserLoginForm


class LoginPageView(LoginView):
    """Класс-контроллер на основе auth.views для входа ранее зарегистрированного пользователя в систему."""

    form_class = AppUserLoginForm
    template_name = "users/login_page.html"
    success_url = reverse_lazy("core:home_page")

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) В текущей реализации передаем:
            - Заголовок страницы (title)
            - Тип страницы для выбора подходящего меню для данный страницы
        3) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["title_login_page_view"] = "Вход в личный кабинет сервиса ОПОРА"
        context["menu_variant"] = "login"
        return context

    def get_success_url(self):
        """Явно указываю редирект переопределяя метод, так как обычный вариант в виде "success_url = reverse_lazy()"
        не работал. Django его игнорировал и отправлял на /accounts/profile/"""
        return reverse_lazy("core:home_page")

    def form_valid(self, form):
        """Автоматический вход пользователя после успешной аутентификации."""
        login(self.request, form.get_user())
        return super().form_valid(form)
