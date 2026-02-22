from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView
from django_ratelimit.decorators import ratelimit

from users._web.forms.edit_client_form import EditClientProfileForm
from users.models import AppUser


@method_decorator(ratelimit(key="ip", rate="5/m", block=True), name="post")
class EditClientProfilePageView(LoginRequiredMixin, FormView):
    """Web-контроллер для редактирования профиля клиента."""

    form_class = EditClientProfileForm
    template_name = "core/client_pages/my_account/edit_client.html"
    success_url = reverse_lazy("users:web:profile-edit")

    def dispatch(self, request, *args, **kwargs):
        """Ограничиваем доступ: редактирование профиля клиента доступно только для role_id=2."""
        if getattr(request.user, "role_id", None) != 2:
            messages.error(request, "Доступ к редактированию профиля клиента ограничен.")
            return redirect("core:start-page")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Передаем текущего пользователя в форму как instance."""
        kwargs = super().get_form_kwargs()
        # Берем пользователя заново из БД, чтобы не мутировать request.user при невалидном POST.
        kwargs["instance"] = AppUser.objects.get(pk=self.request.user.pk)

        return kwargs

    def get_context_data(self, **kwargs):
        """Формирование контекста страницы редактирования профиля клиента.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) В текущей реализации передаем:
            - Заголовок страницы (title)
            - Параметр для настройки отображения меню/навигация
            - Параметр для подсветки выбранного пункта в навигации
            - Текущие initial-данные пользователя из БД
        3) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["title_edit_client_page_view"] = "Редактирование профиля в сервисе ОПОРА"

        # Параметр, который передаем в menu.html и на его основе там настраиваем показ САЙДБАРА
        context["show_sidebar"] = "sidebar"

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "profile-edit"

        # Отдельный "чистый" объект из БД для initial-данных (не связан с form.instance).
        context["db_user"] = AppUser.objects.get(pk=self.request.user.pk)

        return context

    def form_valid(self, form):
        """Сохраняем данные профиля и выводим сообщение."""
        form.save()
        messages.success(self.request, "Данные профиля обновлены.")

        return super().form_valid(form)
