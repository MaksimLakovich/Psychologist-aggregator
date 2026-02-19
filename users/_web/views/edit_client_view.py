from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView
from django_ratelimit.decorators import ratelimit
from users._web.forms.edit_client_form import EditClientProfileForm


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
        kwargs["instance"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Формирование контекста страницы редактирования профиля клиента."""
        context = super().get_context_data(**kwargs)
        context["title_edit_client_page_view"] = "Редактирование профиля в сервисе ОПОРА"

        # Параметр, который передаем в menu.html и на его основе там настраиваем показ боков.НАВИГАЦИЙ / верх.МЕНЮ
        # Данный IF/ELSE позволяет нам задать отдельный параметр для клиента и для психолога, что позволит потом,
        # при необходимости, рендерить разные шаблоны страниц или использовать разный доп функционал
        if getattr(self.request.user, "role_id", None) == 2:
            context["profile_type"] = "client"
        else:
            context["profile_type"] = "psychologist"

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "profile-edit"
        return context

    def form_valid(self, form):
        """Сохраняем данные профиля и выводим сообщение."""
        form.save()
        messages.success(self.request, "Данные профиля обновлены.")
        return super().form_valid(form)
