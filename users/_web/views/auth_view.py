import random

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.views.generic.edit import FormView
from django_ratelimit.decorators import ratelimit

from users._web.forms.auth_form import (AppUserLoginForm,
                                        AppUserRegistrationForm)
from users.mixins.anonymous_only_mixin import AnonymousOnlyMixin
from users.models import AppUser, ClientProfile, PsychologistProfile, UserRole
from users.services.send_verification_email import send_verification_email


@method_decorator(ratelimit(key="ip", rate="5/m", block=True), name="post")
class RegisterPageView(AnonymousOnlyMixin, FormView):
    """Класс-контроллер для регистрации нового пользователя в системе."""

    form_class = AppUserRegistrationForm
    template_name = "users/register_page.html"
    success_url = reverse_lazy("users:web:login-page")  # Редирект после регистрации

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) В текущей реализации передаем:
            - Заголовок страницы (title)
            - Тип страницы для выбора подходящего меню для данной страницы
        3) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["title_register_page_view"] = "Регистрация в сервисе ОПОРА"
        context["menu_variant"] = "without-any-menu"

        return context

    def form_valid(self, form):
        """Регистрация с нейтральным ответом (anti user-enumeration)."""
        email = form.cleaned_data["email"]
        existing_user = AppUser.objects.filter(email=email).first()

        # На случай, если такой пользователь уже есть в БД, но он не подтвердил регистрацию (повторное письмо)
        if existing_user:
            if not existing_user.is_active:
                send_verification_email(existing_user, url_name="users:web:verify-email")

            messages.info(
                self.request,
                "Мы отправили инструкцию для подтверждения регистрации.\nПожалуйста, проверьте вашу почту.",
            )
            return super().form_valid(form)

        # На случай, если в БД в справочнике ролей отсутствует главная базовая роль client
        role_obj = UserRole.objects.filter(role="client").first()
        if not role_obj:
            form.add_error(None, "Отсутствует роль для профиля клиента. Обратитесь в поддержку.")
            return self.form_invalid(form)

        password = form.cleaned_data["password1"]

        # transaction.atomic() - это менеджер контекста в Django, который гарантирует, что весь блок кода внутри него
        # будет выполнен как единая неделимая операция в базе данных
        with transaction.atomic():
            user = AppUser.objects.create_user(
                email=email,
                password=password,
                first_name=form.cleaned_data["first_name"],
                age=form.cleaned_data["age"],
                role=role_obj,
                is_active=False,
            )

            ClientProfile.objects.create(user=user)

        # Отправка письма для подтверждения регистрации
        send_verification_email(user, url_name="users:web:verify-email")
        messages.info(
            self.request,
            "Мы отправили инструкцию для подтверждения регистрации.\nПожалуйста, проверьте вашу почту.",
        )

        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="get")
class VerifyEmailView(AnonymousOnlyMixin, View):
    """Класс-контроллер для верификации email по uid/token и активации пользователя после регистрации."""

    def get(self, request, *args, **kwargs):
        """Метод GET на эндпоинте /verify-email/ для подтверждения email по uid/token, активирует пользователя."""
        uidb64 = request.GET.get("uid")
        token = request.GET.get("token")

        if not uidb64 or not token:
            messages.error(self.request, "Некорректная ссылка подтверждения.")
            return redirect("users:web:login-page")

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = AppUser.objects.get(pk=uid)
        except Exception:
            messages.error(self.request, "Пользователь не найден.")
            return redirect("users:web:login-page")

        if not default_token_generator.check_token(user, token):
            messages.error(self.request, "Ссылка подтверждения недействительна или устарела.")
            return redirect("users:web:login-page")

        # Активируем пользователя
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        messages.success(self.request, "Email успешно подтвержден. Теперь вы можете войти.")

        return redirect("users:web:login-page")


@method_decorator(ratelimit(key="ip", rate="5/m", block=True), name="post")
class LoginPageView(AnonymousOnlyMixin, LoginView):
    """Класс-контроллер на основе auth.views для входа ранее зарегистрированного пользователя в систему."""

    form_class = AppUserLoginForm
    template_name = "users/login_page.html"
    success_url = reverse_lazy("core:general-questions")

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) В текущей реализации передаем:
            - Заголовок страницы (title);
            - Тип страницы для выбора подходящего меню для данный страницы;
            - Количество верифицированных психологов и рандомно 10 аватарок для показа статистики на странице входа;
            - Рандомная цитата.
        3) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)
        context["title_login_page_view"] = "Вход в личный кабинет сервиса ОПОРА"
        context["menu_variant"] = "without-any-menu"
        context["verified_psychologists_count"] = PsychologistProfile.objects.filter(
            is_verified=True
        ).count() + 888
        context["verified_psychologist_avatars"] = (
            PsychologistProfile.objects.filter(is_verified=True)
            .exclude(photo="")
            .exclude(photo__isnull=True)
            .order_by("?")[:10]
        )
        context["login_quote"] = random.choice(
            [
                "«Психотерапия — это искусство возможного. В работе для нас важно сохранять "
                "индивидуальный подход и гибкость в заданных рамках процесса»",
                "«Мы довольно строго отбираем психологов и работаем только с теми, кого смело "
                "могли бы порекомендовать собственным друзьям»",
                "«Мы любим психотерапию и глубоко понимаем её тончайшие нюансы. И наша миссия — "
                "в том, чтобы делиться с людьми этой любовью и пониманием»",
            ]
        )

        return context

    def get_success_url(self):
        """Явно указываю редирект переопределяя метод, так как обычный вариант в виде "success_url = reverse_lazy()"
        не работал. Django его игнорировал и отправлял на /accounts/profile/"""
        return reverse_lazy("core:general-questions")

    def form_valid(self, form):
        """Автоматический вход пользователя после успешной аутентификации."""
        login(self.request, form.get_user())

        return super().form_valid(form)
