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

from calendar_engine.booking.exceptions import \
    CreateTherapySessionValidationError
from calendar_engine.booking.use_cases.therapy_session_create import \
    CreateTherapySessionUseCase
from calendar_engine.models import CalendarEvent
from core.services.anonymous_client_flow_for_search_and_booking import (
    apply_guest_state_to_user, build_choice_psychologist_url,
    build_signed_booking_token, clear_guest_matching_state,
    get_guest_data_for_login, get_guest_data_for_registration,
    get_guest_matching_state, get_guest_pending_booking,
    load_signed_booking_token, update_guest_general_state)
from users._web.forms.auth_form import (AppUserLoginForm,
                                        AppUserRegistrationForm)
from users.mixins.anonymous_only_mixin import AnonymousOnlyMixin
from users.models import AppUser, ClientProfile, PsychologistProfile, UserRole
from users.services.send_verification_email import send_verification_email


@method_decorator(ratelimit(key="ip", rate="5/m", block=True), name="post")
class RegisterPageView(AnonymousOnlyMixin, FormView):
    """Класс-контроллер для регистрации нового пользователя в системе.

    Работает с двумя сценариями:
        - сценарий 1: обычная регистрация без paused-booking;
        - сценарий 2: регистрация после выбора психолога и слота, где после подтверждения email система должна
          попытаться завершить paused-booking автоматически.
    """

    form_class = AppUserRegistrationForm
    template_name = "users/register_page.html"
    success_url = reverse_lazy("users:web:login-page")  # Редирект после регистрации

    def get_initial(self):
        """Подготавливает initial-значения страницы регистрации.

        Если пользователь пришел сюда из сценария "гость", то подтягивается уже введенные ранее и хранящиеся в session
        имя, email и возраст, чтобы не заставлять его вводить их повторно.
        """
        initial = super().get_initial()
        initial.update(get_guest_data_for_registration(self.request.session))
        return initial

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
        # get_guest_pending_booking() возвращает отложенное бронирование guest-anonymous, если оно есть
        context["resume_booking_mode"] = bool(get_guest_pending_booking(self.request.session))

        return context

    def form_valid(self, form):
        """Регистрирует пользователя с нейтральным ответом (anti user-enumeration).

        Работает с двумя сценариями:
            - сценарий 1: обычная регистрация без paused-booking;
            - сценарий 2: регистрация после выбора психолога и слота, где после подтверждения email
              система должна попытаться завершить paused-booking автоматически.
        """
        email = form.cleaned_data["email"]
        # Достает из session текущее временное состояние нового неавторизованного клиента (guest-anonymous-состояние)
        existing_general = get_guest_matching_state(self.request.session)["general"]

        # Сервис update_guest_general_state() нужен здесь, чтобы guest-flow не потерял уже введенные данные
        # первого шага подбора и чтобы регистрация могла использовать их повторно без нового ввода
        update_guest_general_state(
            self.request.session,
            payload={
                "first_name": form.cleaned_data["first_name"],
                "email": email,
                "age": form.cleaned_data["age"],
                "timezone": existing_general.get("timezone", ""),
                "therapy_experience": existing_general.get("therapy_experience", False),
            },
        )
        existing_user = AppUser.objects.filter(email=email).first()

        # 1) Сценарий 1: пользователь с таким email уже есть в БД.
        # Если аккаунт еще не активирован, просто отправляем повторное письмо подтверждения.
        if existing_user:
            if not existing_user.is_active:
                # Сервис apply_guest_state_to_user() переносит guest-ответы из session
                # в реальные модели пользователя, чтобы после подтверждения email
                # его профиль уже был заполнен актуальными данными
                apply_guest_state_to_user(user=existing_user, session=self.request.session)
                # Сервис build_signed_booking_token() собирает безопасный signed-токен
                # для автоматического продолжения paused-booking после подтверждения email
                resume_token = build_signed_booking_token(user=existing_user, session=self.request.session)
                send_verification_email(
                    existing_user,
                    url_name="users:web:verify-email",
                    extra_query_params={"resume_booking": resume_token} if resume_token else None,
                )

            messages.info(
                self.request,
                (
                    "Мы отправили инструкцию для подтверждения регистрации.\n"
                    "Пожалуйста, проверьте вашу почту."
                    if not get_guest_pending_booking(self.request.session)
                    else
                    "Мы отправили письмо для подтверждения регистрации.\n"
                    "После подтверждения email бронирование встречи произойдет автоматически."
                ),
            )
            return super().form_valid(form)

        # 2) Сценарий 2: создаем нового пользователя, если такого email еще нет в системе.
        # На случай, если в БД в справочнике ролей отсутствует главная базовая роль client.
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
            # Сервис apply_guest_state_to_user() сразу переносит guest-данные в созданный аккаунт,
            # чтобы после подтверждения email профиль клиента уже содержал ответы из шага подбора
            apply_guest_state_to_user(user=user, session=self.request.session)

        # Сервис build_signed_booking_token() добавляет в письмо контекст paused-booking,
        # если гость ранее уже выбрал специалиста и слот
        resume_token = build_signed_booking_token(user=user, session=self.request.session)
        send_verification_email(
            user,
            url_name="users:web:verify-email",
            extra_query_params={"resume_booking": resume_token} if resume_token else None,
        )
        messages.info(
            self.request,
            (
                "Мы отправили инструкцию для подтверждения регистрации.\n"
                "Пожалуйста, проверьте вашу почту."
                if not get_guest_pending_booking(self.request.session)
                else
                "Мы отправили письмо для подтверждения регистрации.\n"
                "После подтверждения email бронирование встречи произойдет автоматически."
            ),
        )

        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="get")
class VerifyEmailView(AnonymousOnlyMixin, View):
    """Класс-контроллер для верификации email по uid/token и активации пользователя после регистрации.

    Работает с двумя сценариями:
        - сценарий 1: обычное подтверждение email без resume-booking;
        - сценарий 2: подтверждение email с resume-booking, где после активации система пытается автоматически
          завершить ранее выбранную запись.
    """

    def get(self, request, *args, **kwargs):
        """Подтверждает email и, при необходимости, возобновляет paused-booking."""
        uidb64 = request.GET.get("uid")
        token = request.GET.get("token")
        resume_booking_token = request.GET.get("resume_booking")

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

        # Если пользователь уже активирован, guest-state больше не нужен:
        # сервис clear_guest_matching_state() удаляет временный черновик гостя из session
        if user.is_active:
            clear_guest_matching_state(self.request.session)
            messages.info(self.request, "Email уже подтвержден. Теперь вы можете войти.")
            return redirect("users:web:login-page")

        # Активируем пользователя после успешной проверки uid/token
        user.is_active = True
        user.save(update_fields=["is_active"])

        # Сервис load_signed_booking_token() проверяет подпись resume-токена и, если он валиден, то
        # возвращает данные для продолжения paused-booking
        resume_payload = load_signed_booking_token(resume_booking_token)

        # 1) Сценарий 1: в ссылке есть валидный resume-booking для этого пользователя
        if resume_payload and str(resume_payload.get("user_pk")) == str(user.pk):
            layout_mode = resume_payload.get("layout_mode", "menu")
            login(self.request, user)

            try:
                booking_result = CreateTherapySessionUseCase().execute(
                    client_user=user,
                    specialist_profile_id=resume_payload["specialist_profile_id"],
                    slot_start_iso=resume_payload["slot_start_iso"],
                    consultation_type=resume_payload["consultation_type"],
                )
            except CreateTherapySessionValidationError as exc:
                # Сервис clear_guest_matching_state() очищает старый guest-черновик,
                # потому что он уже не должен повторно использоваться после неудачной попытки resume-booking
                clear_guest_matching_state(self.request.session)
                messages.error(self.request, str(exc))
                # Используется после подтверждения email, если система попыталась автоматом завершить paused-booking,
                # но выбранный слот уже недоступен (например, его забронировал другой клиент или слот уже в прошлом).
                # Тогда пользователя нужно вернуть на шаг выбора психолога и времени в режиме нового повторного выбора
                return redirect(build_choice_psychologist_url(reset=True))

            self.request.session["last_created_booking_id"] = str(booking_result["event"].id)

            # После успешного завершения paused-booking временный guest-state больше не нужен
            clear_guest_matching_state(self.request.session)
            messages.success(self.request, "Email подтвержден, запись успешно завершена.")
            return redirect(f"{reverse_lazy('core:client-planned-sessions')}?layout={layout_mode}")

        # 2) Сценарий 2: обычное подтверждение email без возобновления paused-booking
        clear_guest_matching_state(self.request.session)
        messages.success(self.request, "Email успешно подтвержден. Теперь вы можете войти.")
        return redirect("users:web:login-page")


@method_decorator(ratelimit(key="ip", rate="5/m", block=True), name="post")
class LoginPageView(AnonymousOnlyMixin, LoginView):
    """Класс-контроллер на основе auth.views для входа ранее зарегистрированного пользователя в систему.

    Работает с двумя сценариями:
        - сценарий 1: обычный вход без paused-booking;
        - сценарий 2: вход "гостя" после выбора психолога и слота, где после подтверждения email система должна
          попытаться завершить paused-booking автоматически.
    """

    form_class = AppUserLoginForm
    template_name = "users/login_page.html"
    success_url = reverse_lazy("core:general-questions")

    def get_initial(self):
        """Подготавливает initial-значения страницы входа.

        Если пользователь пришел сюда из сценария "гость", то подтягивается уже введенные ранее и хранящиеся в session
        его email, чтобы не заставлять вводить их повторно.
        """
        initial = super().get_initial()
        initial.update(get_guest_data_for_login(self.request.session))
        return initial

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
        # get_guest_pending_booking() возвращает отложенное бронирование guest-anonymous, если оно есть
        context["resume_booking_mode"] = bool(get_guest_pending_booking(self.request.session))
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

    def _has_planned_or_started_sessions(self, user) -> bool:
        """Проверяет, есть ли у пользователя клиентские события в статусе planned или started.

        Это нужно, чтобы после входа направить пользователя в наиболее логичную точку:
            - если встречи уже есть, открываем страницу "Мой кабинет";
            - если встреч еще нет, открываем первый шаг "Подбор психолога".
        """
        return CalendarEvent.objects.filter(
            participants__user=user,
            status__in=["planned", "started"],
        ).exists()

    def get_success_url(self):
        """Определяет страницу, которую пользователь увидит сразу после успешного входа.

        Логика:
            - если у клиента уже есть события в статусе planned или started, то открываем страницу "Мой кабинет";
            - если таких событий нет, открываем первый шаг "Подбор психолога".
        """
        if self._has_planned_or_started_sessions(self.request.user):
            return reverse_lazy("core:client-account")

        return reverse_lazy("core:general-questions")

    def form_valid(self, form):
        """Выполняет вход пользователя после успешной аутентификации.

        После входа Django вызывает get_success_url(), который выбирает стартовую страницу
        в зависимости от того, есть ли у пользователя уже активные клиентские сессии.
        """
        login(self.request, form.get_user())

        return super().form_valid(form)
