from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.generic.edit import FormView
from django_ratelimit.decorators import ratelimit
from users._web.forms.reset_password_form import PasswordResetConfirmForm, PasswordResetRequestForm
from users.mixins.anonymous_only_mixin import AnonymousOnlyMixin
from users.models import AppUser
from users.services.send_password_reset_email import send_password_reset_email


@method_decorator(ratelimit(key="ip", rate="5/m", block=True), name="post")
class PasswordResetRequestPageView(AnonymousOnlyMixin, FormView):
    """Web-контроллер для запроса восстановления пароля по email (неавторизованный пользователь)."""

    form_class = PasswordResetRequestForm
    template_name = "users/password_reset_request_page.html"
    success_url = reverse_lazy("users:web:login-page")

    def get_context_data(self, **kwargs):
        """Формирование контекста страницы запроса восстановления пароля."""
        context = super().get_context_data(**kwargs)
        context["title_password_reset_request_view"] = "Восстановление пароля в сервисе ОПОРА"
        context["menu_variant"] = "login"
        return context

    def form_valid(self, form):
        """Отправка письма на восстановление пароля (с нейтральным ответом без user-enumeration)."""
        email = form.cleaned_data["email"]
        user = AppUser.objects.filter(email=email).first()

        # Если пользователь найден - отправляем письмо, иначе просто возвращаем нейтральный ответ.
        if user:
            send_password_reset_email(user, url_name="users:web:password-reset-confirm")

        messages.info(
            self.request,
            "Если аккаунт с таким email существует, мы отправили инструкцию для восстановления пароля.",
        )
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="get")
@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="post")
class PasswordResetConfirmPageView(AnonymousOnlyMixin, FormView):
    """Web-контроллер для подтверждения сброса пароля по uid/token и установке нового пароля."""

    form_class = PasswordResetConfirmForm
    template_name = "users/password_reset_confirm_page.html"
    success_url = reverse_lazy("users:web:login-page")

    def dispatch(self, request, *args, **kwargs):
        """Проверяем uid/token до рендера формы и сохраняем пользователя для последующего form_valid()."""
        uidb64 = request.GET.get("uid")
        token = request.GET.get("token")

        if not uidb64 or not token:
            messages.error(request, "Некорректная ссылка для восстановления пароля.")
            return redirect("users:web:login-page")

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            self.user_obj = AppUser.objects.get(pk=uid)
        except Exception:
            messages.error(request, "Пользователь не найден.")
            return redirect("users:web:login-page")

        if not default_token_generator.check_token(self.user_obj, token):
            messages.error(request, "Ссылка для восстановления пароля недействительна или устарела.")
            return redirect("users:web:login-page")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Формирование контекста страницы подтверждения сброса пароля."""
        context = super().get_context_data(**kwargs)
        context["title_password_reset_confirm_view"] = "Подтверждение нового пароля в сервисе ОПОРА"
        context["menu_variant"] = "login"
        return context

    def form_valid(self, form):
        """Сохранение нового пароля для пользователя при валидной ссылке uid/token."""
        self.user_obj.set_password(form.cleaned_data["new_password"])
        self.user_obj.save(update_fields=["password"])

        messages.success(self.request, "Пароль успешно изменен. Теперь вы можете войти.")
        return super().form_valid(form)
