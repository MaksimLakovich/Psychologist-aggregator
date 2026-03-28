import random
from datetime import datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.formats import date_format
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django_ratelimit.decorators import ratelimit

from calendar_engine.booking.exceptions import \
    CreateTherapySessionValidationError
from calendar_engine.booking.services import normalize_user_timezone
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

# ===== Вспомогательные функции для определения куда перенаправлять пользователя при авторизации:
# - на страницу подбора, если нет запланированных событий
# - в личный кабинет, если есть запланированные события


def _has_planned_or_started_sessions(user) -> bool:
    """Проверяет, есть ли у пользователя клиентские события в статусе planned или started.

    Это нужно, чтобы после входа или подтверждения email направить пользователя в наиболее логичную точку:
        - если встречи уже есть, открываем страницу "Мой кабинет";
        - если встреч еще нет, открываем первый шаг "Подбор психолога".
    """
    return CalendarEvent.objects.filter(
        participants__user=user,
        status__in=["planned", "started"],
    ).exists()


def _build_post_login_redirect_url(user) -> str:
    """Возвращает стартовый URL для уже авторизованного клиента.

    Используется в двух местах:
        - после обычного входа по email и паролю;
        - после подтверждения email, когда система автоматически логинит пользователя.
    """
    if _has_planned_or_started_sessions(user):
        return f"{reverse_lazy('core:client-events')}?layout=sidebar"

    return str(reverse_lazy("core:general-questions"))


# ===== Вспомогательные функции для определения отдельного экрана завершения записи для гостя и его наполнения

def _build_complete_booking_auth_url(*, stage: str | None = None) -> str:
    """Собирает URL отдельного экрана завершения записи для гостя.

    Этот экран нужен только для guest paused-booking и решает бизнес-задачу:
        - не смешивать специальный сценарий "завершение записи" с обычными страницами login/register;
        - сначала показать пользователю, что специалист и слот уже сохранены;
        - только потом предложить выбрать: войти в существующий аккаунт или создать новый.
    """
    base_url = str(reverse_lazy("users:web:complete-booking-auth"))

    if not stage:
        return base_url

    return f"{base_url}?{urlencode({'stage': stage})}"


def _build_paused_booking_summary(session) -> dict | None:
    """Готовит предметный summary выбранного специалиста и слота для отдельного экрана завершения записи для гостя.

    Summary нужен, чтобы на отдельном экране завершения записи гость видел не абстрактное сообщение,
    а именно тот выбор, который он уже сделал на шаге payment-card:
        - фото специалиста;
        - имя специалиста;
        - формат и стоимость сессии;
        - дата и время выбранного слота.
    """
    # Возвращает отложенное бронирование guest-anonymous, если оно есть
    pending_booking = get_guest_pending_booking(session)

    if not pending_booking:
        return None

    specialist_profile = (
        PsychologistProfile.objects.select_related("user")
        .filter(pk=pending_booking["specialist_profile_id"])
        .first()
    )
    if not specialist_profile:
        return None

    consultation_type = pending_booking["consultation_type"]
    price_value = (
        specialist_profile.price_couples
        if consultation_type == "couple"
        else specialist_profile.price_individual
    )
    price_label = format(price_value, "f").rstrip("0").rstrip(".")
    session_label = (
        "Парная сессия · 1,5 часа"
        if consultation_type == "couple"
        else "Индивидуальная сессия · 50 минут"
    )
    slot_start_datetime = datetime.fromisoformat(pending_booking["slot_start_iso"])
    guest_timezone_value = get_guest_matching_state(session)["general"].get("timezone")
    guest_timezone = (
        normalize_user_timezone(timezone_value=guest_timezone_value)
        if guest_timezone_value
        else timezone.get_default_timezone()
    )
    slot_start_local = timezone.localtime(slot_start_datetime, guest_timezone)

    return {
        "specialist_photo_url": specialist_profile.user.avatar_url,
        "specialist_full_name": (
            f"{specialist_profile.user.first_name} {specialist_profile.user.last_name}".strip()
            or specialist_profile.user.email
        ),
        "session_summary": f"{session_label} · {price_label} {specialist_profile.price_currency}",
        "slot_summary": (
            f"{date_format(slot_start_local, 'j F')} "
            f"{slot_start_local.strftime('%H:%M')} "
            f"({date_format(slot_start_local, 'l').lower()})"
        ),
    }


# ===== Вспомогательная функция, которая потом используется для завершения paused-booking при завершении
# регистрации или входа гостя

def _resume_pending_booking_after_authentication(request, *, user, booking_payload: dict, success_message: str):
    """Пытается сразу завершить paused-booking после успешной аутентификации.

    Используется в двух местах:
        - после входа существующего пользователя по email и паролю;
        - после подтверждения email, когда новый пользователь автоматически логинится.

    Бизнес-правило:
        - если слот все еще доступен, запись завершается автоматически;
        - если слот уже занят или больше недоступен, guest-черновик очищается,
          а пользователя возвращают на шаг выбора психолога у того же специалиста.
    """
    try:
        booking_result = CreateTherapySessionUseCase().execute(
            client_user=user,
            specialist_profile_id=booking_payload["specialist_profile_id"],
            slot_start_iso=booking_payload["slot_start_iso"],
            consultation_type=booking_payload["consultation_type"],
        )
    except CreateTherapySessionValidationError as exc:
        # Сервис clear_guest_matching_state() очищает старый guest-черновик,
        # потому что он уже не должен повторно использоваться после неудачной попытки resume-booking
        clear_guest_matching_state(request.session)
        # Используется после подтверждения email, если система попыталась автоматом завершить paused-booking,
        # но выбранный слот уже недоступен (например, его забронировал другой клиент или слот уже в прошлом).
        # Тогда пользователя нужно вернуть на шаг выбора психолога и времени.
        # ВАЖНО: здесь нельзя передавать reset=1 (True), потому что reset-сценарий специально сбрасывает выбор
        # текущего специалиста и открывает первую аву из выдачи. А в этом кейсе пользователю, наоборот,
        # нужно сохранить ранее выбранного специалиста и предложить только выбрать другое время.
        messages.error(request, str(exc))
        return redirect(
            build_choice_psychologist_url(
                reset=False,
                specialist_profile_id=booking_payload["specialist_profile_id"],
            )
        )

    request.session["last_created_booking_id"] = str(booking_result["event"].id)

    # После успешного завершения paused-booking временный guest-state больше не нужен
    clear_guest_matching_state(request.session)
    messages.success(request, success_message)

    return redirect(f"{reverse_lazy('core:client-events')}?layout=sidebar")


# ===== ЗАВЕРШЕНИЕ БРОНИ У ГОСТЯ =====

class CompleteBookingAuthPageView(AnonymousOnlyMixin, TemplateView):
    """Отдельный экран выбора следующего шага для гостя с paused-booking.

    Экран появляется только после того, как гость уже выбрал специалиста и слот, а система поставила запись
    на паузу до аутентификации.
    """

    template_name = "users/complete_booking_auth_page.html"

    def get(self, request, *args, **kwargs):
        """Показывает экран завершения записи только если в session действительно есть paused-booking."""
        if not get_guest_pending_booking(request.session):
            return redirect("users:web:login-page")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Формирует контекст отдельного guest-экрана завершения записи."""
        context = super().get_context_data(**kwargs)
        context["title_complete_booking_auth_view"] = "Завершение записи в сервисе ОПОРА"
        context["booking_auth_stage"] = self.request.GET.get("stage", "choose-auth-method")
        context["booking_summary"] = _build_paused_booking_summary(self.request.session)
        context["login_url"] = reverse_lazy("users:web:login-page")
        context["register_url"] = reverse_lazy("users:web:register-page")
        context["guest_email"] = get_guest_matching_state(self.request.session)["general"].get("email", "")
        return context


# ===== РЕГИСТРАЦИЯ НОВОГО ПООЛЬЗОВАТЕЛЯ =====

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
        # get_guest_pending_booking() возвращает отложенное бронирование guest-anonymous, если оно есть
        has_paused_booking = bool(get_guest_pending_booking(self.request.session))

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
                # Сценарий paused-booking: после регистрации не отправляем гостя на базовую login-страницу,
                # а показываем отдельный экран с понятным следующим шагом - подтвердить email
                if has_paused_booking:
                    return redirect(_build_complete_booking_auth_url(stage="verification-pending"))

                messages.info(
                    self.request,
                    "Мы отправили инструкцию для подтверждения регистрации.\n"
                    "Пожалуйста, проверьте вашу почту.",
                )
                return super().form_valid(form)

            # Для гостя с paused-booking здесь нужен явный продуктовый сценарий:
            # email уже принадлежит активному аккаунту, значит запись можно завершить только через вход
            if has_paused_booking:
                return redirect(_build_complete_booking_auth_url(stage="account-exists"))

            messages.info(
                self.request,
                "Если аккаунт с таким email существует, вы можете войти в систему или восстановить пароль.",
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

        if has_paused_booking:
            return redirect(_build_complete_booking_auth_url(stage="verification-pending"))

        messages.info(
            self.request,
            "Мы отправили инструкцию для подтверждения регистрации.\n"
            "Пожалуйста, проверьте вашу почту.",
        )

        return super().form_valid(form)


# ===== ПОДТВЕРЖДЕНИЕ И АКТИВАЦИЯ НОВОГО ПОЛЬЗОВАТЕЛЯ =====

@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="get")
class VerifyEmailView(AnonymousOnlyMixin, View):
    """Класс-контроллер для верификации email по uid/token и активации пользователя после регистрации.

    Работает с двумя сценариями:
        - сценарий 1: обычное подтверждение email без resume-booking;
        - сценарий 2: подтверждение email с resume-booking, где после активации система пытается автоматически
          завершить ранее выбранную запись.
    """

    def get(self, request, *args, **kwargs):
        """Подтверждает email и, при необходимости, возобновляет paused-booking.

        После успешного подтверждения система автоматически логинит пользователя,
        чтобы ему не приходилось повторно вводить email и пароль.
        """
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

        # Если пользователь уже активирован и ссылка валидна, повторно подтверждать ничего не нужно.
        # Но для удобства все равно автоматически логиним пользователя и ведем его дальше как в обычном post-login.
        if user.is_active:
            login(self.request, user)
            resume_payload = load_signed_booking_token(resume_booking_token)
            if resume_payload and str(resume_payload.get("user_pk")) == str(user.pk):
                return _resume_pending_booking_after_authentication(
                    self.request,
                    user=user,
                    booking_payload=resume_payload,
                    success_message="Email уже был подтвержден, запись успешно завершена.",
                )

            clear_guest_matching_state(self.request.session)
            messages.info(self.request, "Email уже был подтвержден. Вы уже вошли в систему")
            return redirect(_build_post_login_redirect_url(user))

        # Активируем пользователя после успешной проверки uid/token
        user.is_active = True
        user.save(update_fields=["is_active"])

        # Сервис load_signed_booking_token() проверяет подпись resume-токена и, если он валиден, то
        # возвращает данные для продолжения paused-booking
        resume_payload = load_signed_booking_token(resume_booking_token)

        # 1) Сценарий 1: в ссылке есть валидный resume-booking для этого пользователя
        if resume_payload and str(resume_payload.get("user_pk")) == str(user.pk):
            login(self.request, user)
            return _resume_pending_booking_after_authentication(
                self.request,
                user=user,
                booking_payload=resume_payload,
                success_message="Email подтвержден, запись успешно завершена.",
            )

        # 2) Сценарий 2: обычное подтверждение email без возобновления paused-booking
        login(self.request, user)
        clear_guest_matching_state(self.request.session)
        messages.success(self.request, "Email успешно подтвержден. Вы уже вошли в систему")
        return redirect(_build_post_login_redirect_url(user))


# ===== ВХОД =====

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
        """Определяет страницу, которую пользователь увидит сразу после успешного входа.

        Логика:
            - если у клиента уже есть события в статусе planned или started, то открываем страницу "Мой кабинет";
            - если таких событий нет, открываем первый шаг "Подбор психолога".
        """
        return _build_post_login_redirect_url(self.request.user)

    def form_valid(self, form):
        """Выполняет вход пользователя после успешной аутентификации.

        Работает в двух сценариях:
            - сценарий 1: обычный вход без paused-booking;
            - сценарий 2: вход после guest paused-booking, где запись нужно попытаться завершить автоматически.
        """
        user = form.get_user()
        login(self.request, user)

        # Сценарий 2: если перед входом у гостя уже была поставлена на паузу запись,
        # пытаемся завершить ее сразу после успешной аутентификации.
        pending_booking = get_guest_pending_booking(self.request.session)
        if pending_booking:
            return _resume_pending_booking_after_authentication(
                self.request,
                user=user,
                booking_payload=pending_booking,
                success_message="Вход выполнен, запись успешно завершена.",
            )

        # Сценарий 1: обычный вход в систему без paused-booking.
        return redirect(self.get_success_url())
