from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView
from django_ratelimit.decorators import ratelimit

from users._web.forms.change_password_form import ChangePasswordForm


@method_decorator(ratelimit(key="ip", rate="5/m", block=True), name="post")
class ChangePasswordPageView(LoginRequiredMixin, FormView):
    """Web-контроллер для смены пароля авторизованного пользователя."""

    form_class = ChangePasswordForm
    template_name = "core/client_pages/my_account/change_password.html"
    success_url = reverse_lazy("users:web:password-change")

    def get_form_kwargs(self):
        """Передаем пользователя в форму для проверки текущего пароля."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Формирование контекста страницы смены пароля."""
        context = super().get_context_data(**kwargs)
        context["title_change_password_view"] = "Смена пароля в сервисе ОПОРА"

        # Параметр, который передаем в menu.html и на его основе там настраиваем показ боков.НАВИГАЦИЙ / верх.МЕНЮ
        # Данный IF/ELSE позволяет нам задать отдельный параметр для клиента и для психолога, что позволит потом,
        # при необходимости, рендерить разные шаблоны страниц или использовать разный доп функционал
        if getattr(self.request.user, "role_id", None) == 2:
            context["profile_type"] = "client"
        else:
            context["profile_type"] = "psychologist"

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "password-change"
        # Одноразовый флаг успешной смены пароля (для показа экрана успеха вместо формы).
        context["password_changed"] = self.request.session.pop("password_changed", False)
        return context

    def form_valid(self, form):
        """Сохраняем новый пароль и оставляем пользователя авторизованным."""
        user = self.request.user
        user.set_password(form.cleaned_data["new_password"])
        user.save(update_fields=["password"])

        # Сохраняем сессию после смены пароля (без выхода из аккаунта).
        update_session_auth_hash(self.request, user)

        # Одноразовый флаг для UI: покажем экран успеха и уберем форму.
        self.request.session["password_changed"] = True
        return super().form_valid(form)
