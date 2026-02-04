from datetime import datetime, tzinfo
from zoneinfo import ZoneInfo

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.timezone import is_naive, make_aware, now
from django.views import View
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import (BlacklistedToken,
                                                             OutstandingToken)
from rest_framework_simplejwt.views import TokenObtainPairView

from calendar_engine.application.factories.generate_specialist_schedule_factory import \
    build_generate_specialist_schedule_use_case
from calendar_engine.application.use_cases.get_domain_slots_use_case import \
    GetDomainSlotsUseCase
from calendar_engine.models import AvailabilityException, AvailabilityRule
from users._api.serializers import (AppUserSerializer,
                                    AvailabilityExceptionSerializer,
                                    AvailabilityRuleSerializer,
                                    ChangePasswordSerializer,
                                    ClientProfileReadSerializer,
                                    ClientProfileWriteSerializer,
                                    CustomTokenObtainPairSerializer,
                                    EducationSerializer, LogoutSerializer,
                                    MethodSerializer,
                                    PasswordResetConfirmSerializer,
                                    PasswordResetSerializer,
                                    PsychologistProfileReadSerializer,
                                    PsychologistProfileWriteSerializer,
                                    PublicPsychologistProfileSerializer,
                                    RegisterSerializer,
                                    SpecialisationSerializer, TopicSerializer)
from users.constants import (AGE_BUCKET_CHOICES, ALLOWED_REGISTER_ROLES,
                             GENDER_CHOICES, PREFERRED_TOPIC_TYPE_CHOICES)
from users.models import (AppUser, ClientProfile, Education, Method,
                          PsychologistProfile, Specialisation, Topic, UserRole)
from users.permissions import (IsOwnerOrAdmin, IsProfileOwnerOrAdmin,
                               IsProfileOwnerOrAdminMixin,
                               IsPsychologistOrAdmin, IsSelfOrAdmin)
from users.services.send_password_reset_email import send_password_reset_email
from users.services.send_verification_email import send_verification_email
from users.services.throttles import (ChangePasswordThrottle, LoginThrottle,
                                      PasswordResetConfirmThrottle,
                                      PasswordResetThrottle, RegisterThrottle,
                                      ResendThrottle)

# =====
# РЕГИСТРАЦИЯ / АВТОРИЗАЦИЙ / ПАРОЛИ / ВЫХОД
# =====


class RegisterView(generics.GenericAPIView):
    """Класс-контроллер на основе базового GenericAPIView для регистрации:
     1) Нового пользователя с профилем 'Психолог', если параметр role = psychologist.
     2) Нового пользователя с профилем 'Клиент', если параметр role = client."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]  # Добавляю throttle (anti-spam) для email на подтверждение активации

    def post(self, request, *args, **kwargs):
        """Метод POST на эндпоинте /register/ для создания нового пользователя и связанного профиля
        в зависимости от указанной роли (psychologist / client)."""
        role_value = request.data.get("role")

        # Эта первая проверка - это валидация пользовательского ввода (то, что указали в теле запроса).
        if role_value not in ALLOWED_REGISTER_ROLES:
            return Response(
                data={"detail": "Неверная или недопустимая роль."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_role = UserRole.objects.get(role=role_value)
        # Эта вторая проверка - это уже валидация данных в базе данных.
        except UserRole.DoesNotExist:
            return Response(
                data={"detail": "Роль не найдена."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data, context={"role": user_role})
        serializer.is_valid(raise_exception=True)  # иначе данные не будут валидироваться
        serializer.save()  # должен вызываться, иначе пользователь не создастся

        # Эта часть проверяет - существует ли флаг "inactive_user_resend = True" и если существует, то значит
        # это повторная отправка письма, а поэтому, вместо обычного json-ответа с данными пользователя, будем
        # возвращать красивый ответ "verification_resent"
        if serializer.context.get("inactive_user_resend"):
            return Response(
                {
                    "status": "verification_resent",
                    "message": "Пользователь уже существует, но не активен. Отправили новое письмо для подтверждения."
                },
                status=status.HTTP_200_OK
            )

        return Response(data=serializer.data, status=status.HTTP_201_CREATED)


class EmailVerificationView(APIView):
    """Класс-контроллер на основе APIView для подтверждения email и активации пользователя после регистрации."""

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        """Метод GET на эндпоинте /verify-email/ для подтверждения email по uid и token, активирует пользователя."""
        uidb64 = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uidb64 or not token:
            return Response(
                {"detail": "Некорректная ссылка."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = AppUser.objects.get(pk=uid)
        except Exception:
            return Response(
                {"detail": "Пользователь не найден."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Недействительный или просроченный токен."}, status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_active:
            return Response(
                {"detail": "Email уже подтвержден."}, status=status.HTTP_200_OK
            )

        # Активируем пользователя
        user.is_active = True
        user.save()

        return Response(
            {"detail": "Email успешно подтвержден!"}, status=status.HTTP_200_OK
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Класс-контроллер на основе TokenObtainPairView для авторизации по email."""

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]  # type: ignore[assignment]
    throttle_classes = [LoginThrottle]  # Добавляю throttle для безопасности системы (сейчас у нас по IP, а не email)


class LogoutAPIView(APIView):
    """Класс-контроллер на основе APIView для реального выхода пользователя из системы.
    Добавляет его refresh токен в blacklist, делая невозможным дальнейшее обновление access токена."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Метод POST на эндпоинте /logout/ для выполнения реального выхода из системы:
            1. Принимает refresh-токен от клиента.
            2. Валидирует его с помощью LogoutSerializer.
            3. Заносит токен в blacklist.
            4. Возвращает код 205 (Reset Content), чтобы фронтенд сбросил состояние.
        После этого refresh-токен становится полностью недействительным."""
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # 205 - это стандартный HTTP-код, который браузеры используют для "сбросить состояние клиента".
        return Response({"detail": "Успешный выход."}, status=status.HTTP_205_RESET_CONTENT)


class ResendEmailVerificationView(APIView):
    """Класс-контроллер на основе APIView для запроса на повторное подтверждения email и активации пользователя
    после регистрации (если предыдущее не было использовано)."""

    permission_classes = [AllowAny]
    throttle_classes = [ResendThrottle]  # Добавляю throttle (anti-spam) для запроса повторной отправки email

    def post(self, request, *args, **kwargs):
        """Метод POST на эндпоинте /resend-verify-email/ для повторной отправки письма с подтверждением email,
        если пользователь уже существует в БД, но еще не активирован."""
        email = request.data.get("email")

        if not email:
            return Response(
                {"detail": "Email обязателен."}, status=status.HTTP_400_BAD_REQUEST
            )

        user = AppUser.objects.filter(email=email).first()

        if not user:
            return Response(
                {"detail": "Пользователь с таким email не найден."}, status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_active:
            return Response(
                {"detail": "Email уже подтвержден."}, status=status.HTTP_200_OK
            )

        # Повторная отправка email с подтверждением регистрации
        send_verification_email(user)

        return Response(
            {"detail": "Письмо повторно отправлено."}, status=status.HTTP_200_OK
        )


class ChangePasswordView(APIView):
    """Класс-контроллер на основе APIView для изменения пароля авторизованным пользователем."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ChangePasswordThrottle]

    def post(self, request, *args, **kwargs):
        """Метод POST на эндпоинте /change-password/ для изменения пароля авторизованным пользователем."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "Пароль успешно изменен."},
            status=status.HTTP_200_OK
        )


class PasswordResetView(APIView):
    """Класс-контроллер на основе APIView для сброса пароля неавторизованного пользователя."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request, *args, **kwargs):
        """Метод POST на эндпоинте /password-reset/ для сброса пароля неавторизованного пользователя.
        Принимает email, и если пользователь найден и не заблокирован - отправляет письмо для сброса пароля.
        По соображениям безопасности всегда возвращает одинаковый ответ (чтобы не сливать инфо о наличии аккаунта)."""
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = AppUser.objects.filter(email=email).first()

        # Если пользователь найден - отправляем письмо.
        if user:
            send_password_reset_email(user)

        # Всегда нужно отвечать нейтрально, не раскрывая, найден пользователь или нет.
        return Response(
            data={"detail": "Если аккаунт с таким email существует, то мы отправили на него инструкцию."},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    """Класс-контроллер на основе APIView для подтверждения сброса пароля неавторизованного пользователя."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetConfirmThrottle]

    def post(self, request, *args, **kwargs):
        """Метод POST на эндпоинте /password-reset-confirm/ для подтверждения сброса пароля пользователя.
        Принимает uid, token, new_password, new_password_confirm.
        Меняет пароль при валидном токене."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data={"detail": "Пароль успешно изменен."}, status=status.HTTP_200_OK
        )


# =====
# ПОЛЬЗОВАТЕЛИ СИСТЕМЫ
# =====

class AppUserRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """Класс-контроллер на основе Generic для работы с одним конкретным AppUser (аккаунт):
        - получение данных текущего пользователя;
        - редактирование данных;
        - soft-delete: вместо DESTROY-запроса (устанавливаем is_active=False и блокируем токены)."""

    permission_classes = [IsAuthenticated, IsSelfOrAdmin]
    serializer_class = AppUserSerializer

    def get_object(self):
        """Не указываем queryset для AppUser на уровне класса (DRF best practice),
        напрямую возвращаем объект (всегда работаем с текущим пользователем)."""
        return self.request.user

    def perform_update(self, serializer):
        """Если пользователь меняет email - требуем повторную верификацию/активацию:
            - если email изменился, помечаем user.is_active=False и отправляем письмо для новой активации.
            - если меняются остальные данные, то без повторной активации аккаунта."""
        user = self.get_object()
        old_email = user.email
        user = serializer.save()

        # При смене email - требуем повторную верификацию
        if old_email != user.email:
            user.is_active = False
            user.save()
            send_verification_email(user)

    def delete(self, request, *args, **kwargs):
        """Soft-delete: помечаем is_active=False.
        Дополнительно: заносим все outstanding tokens в blacklist, чтобы никто не мог рефрешить токен."""
        user = self.get_object()
        user.is_active = False
        user.save()

        # Blacklist все outstanding-tokens для этого пользователя
        try:
            outstanding_tokens = OutstandingToken.objects.filter(user=user)
            for token in outstanding_tokens:
                # Безопасно: создаем BlacklistedToken, если его еще нет
                BlacklistedToken.objects.get_or_create(token=token)
        except Exception:
            # не фатально - логируем при продакшн-логах
            pass

        return Response(status=status.HTTP_204_NO_CONTENT)


class PsychologistProfileRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """Класс-контроллер на основе Generic для работы с профилем психолога текущего пользователя:
        - получение данных профиля психолога для текущего пользователя;
        - редактирование данных."""

    permission_classes = [IsAuthenticated, IsProfileOwnerOrAdmin]

    def get_serializer_class(self):
        """Метод для определения сериализатора в зависимости от запроса:
            - GET: read-сериализатор;
            - PUT/PATCH : write-сериализатор."""
        if self.request.method in ("PUT", "PATCH"):
            return PsychologistProfileWriteSerializer
        return PsychologistProfileReadSerializer

    def get_object(self):
        """Не указываем queryset для PsychologistProfile на уровне класса (DRF best practice),
        напрямую возвращаем объект (всегда работаем с профилем текущего пользователя)."""
        user = self.request.user

        if user.role.role != "psychologist":
            raise PermissionDenied("Доступно только психологам.")

        # это related_name="psychologist_profile" в модели PsychologistProfile и поэтому получаю связанный
        # профиль (один-к-одному) из AppUser.
        # Это удобнее и короче, чем PsychologistProfile.objects.get(user=user) -  по смыслу одно и то же,
        # но user.psychologist_profile читается проще и отражает "у пользователя есть свой профиль".
        try:
            return user.psychologist_profile
        except PsychologistProfile.DoesNotExist:
            raise NotFound("У текущего пользователя нет профиля психолога.")


class PublicPsychologistProfileRetrieveView(generics.RetrieveAPIView):
    """Класс-контроллер на основе Generic для получения данных *Публичного профиля психолога* любым
    авторизованным пользователем системы (скрыты персональные секретные данные - телефон, email и так далее)."""

    permission_classes = [IsAuthenticated]
    serializer_class = PublicPsychologistProfileSerializer
    queryset = PsychologistProfile.objects.select_related("user").all()

    lookup_field = "user__uuid"  # поле в модели
    lookup_url_kwarg = "uuid"  # имя аргумента, которое будем использоать в URL


class ClientProfileRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """Класс-контроллер на основе Generic для работы с профилем клиента текущего пользователя:
        - получение данных профиля клиента для текущего пользователя;
        - редактирование данных."""

    permission_classes = [IsAuthenticated, IsProfileOwnerOrAdmin]

    def get_serializer_class(self):
        """Метод для определения сериализатора в зависимости от запроса:
            - GET: read-сериализатор;
            - PUT/PATCH : write-сериализатор."""
        if self.request.method in ("PUT", "PATCH"):
            return ClientProfileWriteSerializer
        return ClientProfileReadSerializer

    def get_object(self):
        """Не указываем queryset для ClientProfile на уровне класса (DRF best practice),
        напрямую возвращаем объект (всегда работаем с профилем текущего пользователя)."""
        user = self.request.user

        if user.role.role != "client":
            raise PermissionDenied("Доступно только клиентам.")

        # это related_name="client_profile" в модели ClientProfile и поэтому получаю связанный
        # профиль (один-к-одному) из AppUser.
        # Это удобнее и короче, чем ClientProfile.objects.get(user=user) -  по смыслу одно и то же,
        # но user.client_profile читается проще и отражает "у пользователя есть свой профиль".
        try:
            return user.client_profile
        except ClientProfile.DoesNotExist:
            raise NotFound("У текущего пользователя нет профиля клиента.")


# =====
# РАБОЧИЙ ГРАФИК ПСИХОЛОГА
# =====

class AvailabilityRuleListCreateView(generics.ListCreateAPIView):
    """Класс-контроллер на основе Generic для управления рабочим расписанием специалиста.
    Возможности:
    1) GET (200_OK):
        - по умолчанию возвращает только активное правило (is_active=True)
        - include_archived=true -> возвращает все правила (включая архивные)
    2) POST (201_CREATED):
        - создает новое правило доступности (рабочее расписание)
        - при создании нового автоматически деактивируется предыдущее активное правило
        - автоматически проставляет creator и timezone"""

    permission_classes = [IsAuthenticated, IsPsychologistOrAdmin]
    serializer_class = AvailabilityRuleSerializer

    def get_queryset(self):
        """Возвращает правила доступности текущего пользователя. По умолчанию - только активное правило."""
        user = self.request.user
        include_archived = self.request.query_params.get("include_archived")

        queryset = (
            AvailabilityRule.objects
            .filter(creator=user)
            .prefetch_related("time_windows")
        )

        if include_archived not in ("true", "1", "yes"):
            queryset = queryset.filter(is_active=True)

        return queryset.order_by("-created_at")

    @transaction.atomic  # Отвечает за то, чтоб итоговое сохранение произошло только при успешном завершении всех шагов
    def perform_create(self, serializer):
        """Метод для создания нового рабочего расписания.
        Алгоритм:
            1) деактивировать текущее активное правило (если есть)
            2) создать новое правило как is_active=True
            3) timezone берется из профиля пользователя"""
        user = self.request.user

        # Ищем существующее активное правило и деактивируем его перед сохранением нового правила
        # (у специалиста может быть только 1 активное правило)
        AvailabilityRule.objects.filter(
            creator=user,
            is_active=True,
        ).update(is_active=False)

        serializer.save(
            timezone=getattr(user, "timezone", None),
            is_active=True,
        )


class AvailabilityRuleDeactivateView(APIView):
    """Класс-контроллер на основе APIView для явного "закрытия" рабочего расписания специалиста.
    Возможности:
    1) PATCH:
        - по умолчанию возвращает только активное правило (is_active=True)
        - soft-delete: вместо DESTROY-запроса (устанавливаем is_active=False)."""

    permission_classes = [IsAuthenticated, IsPsychologistOrAdmin]

    def patch(self, request, *args, **kwargs):
        """Soft-delete для явного "закрытия" рабочего расписания специалиста: помечаем is_active=False."""
        user = request.user

        rule = AvailabilityRule.objects.filter(
            creator=user,
            is_active=True,
        ).first()

        if not rule:
            return Response(
                data={"detail": "Активное рабочее расписание не найдено"},
                status=status.HTTP_404_NOT_FOUND
            )

        rule.is_active = False
        rule.save(update_fields=["is_active"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class AvailabilityExceptionListCreateView(generics.ListCreateAPIView):
    """Класс-контроллер на основе Generic для управления исключениями в рабочем расписании специалиста.
    Возможности:
    1) GET (200_OK):
        - по умолчанию возвращает только активные исключения (is_active=True)
        - include_archived=true -> возвращает все исключения (включая архивные)
    2) POST (201_CREATED):
        - создает новое исключение из рабочего расписания
        - автоматическая привязка исключения к действующему AvailabilityRule(is_active=True)
        - автоматически проставляет creator"""

    permission_classes = [IsAuthenticated, IsPsychologistOrAdmin]
    serializer_class = AvailabilityExceptionSerializer

    def get_queryset(self):
        """Возвращает исключения из рабочего расписания. По умолчанию - только активные исключения."""
        user = self.request.user
        include_archived = self.request.query_params.get("include_archived")

        queryset = (
            AvailabilityException.objects
            .filter(creator=user)
            .select_related("rule")
            .prefetch_related("time_windows")
        )

        if include_archived not in ("true", "1", "yes"):
            queryset = queryset.filter(is_active=True)

        return queryset.order_by("-created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        """Метод для создания нового исключения в рабочем расписании.
        Алгоритм:
            1) создать новое исключение как is_active=True
            2) автоматическая привязка исключения к действующему AvailabilityRule(is_active=True)
            3) автоматически проставляет creator"""
        user = self.request.user

        # Ищем существующее активное правило
        rule = AvailabilityRule.objects.filter(
            creator=user,
            is_active=True,
        ).first()

        if not rule:
            raise NotFound(
                {"Активное рабочее расписание не найдено"}
            )

        serializer.save(
            rule=rule,
            is_active=True,
        )


class AvailabilityExceptionDeactivateView(APIView):
    """Класс-контроллер на основе APIView для явного "закрытия" исключения из расписания специалиста. В реальной жизни:
        - больничный отменили
        - отпуск сократили
        - day-off перенесли
    Возможности:
    1) PATCH:
        - применяется только к действующим активным исключениям (is_active=True)
        - soft-delete: вместо DESTROY-запроса (устанавливаем is_active=False)."""

    permission_classes = [IsAuthenticated, IsPsychologistOrAdmin]

    def patch(self, request, *args, **kwargs):
        """Soft-delete для явного "закрытия" исключения из рабочего расписания специалиста: is_active=False."""
        user = request.user

        exception = get_object_or_404(
            AvailabilityException,
            creator=user,
            pk=kwargs["pk"],
            is_active=True,
        )

        exception.is_active = False
        exception.save(update_fields=["is_active"])

        return Response(status=status.HTTP_204_NO_CONTENT)


# =====
# ОБЩИЕ СПРАВОЧНИКИ СИСТЕМЫ
# =====

class TopicListView(generics.ListAPIView):
    """Класс-контроллер на основе Generic для получения списка всех Topics.
    Используется, например, при выборе темы в профиле клиента/психолога."""

    permission_classes = [AllowAny]
    serializer_class = TopicSerializer
    queryset = Topic.objects.all().order_by("type", "group_name", "name")


class TopicDetailView(generics.RetrieveAPIView):
    """Класс-контроллер на основе Generic для получения подробной информации по Topic.
    Поиск записи выполняется по полю slug (человекочитаемый URL)."""

    permission_classes = [AllowAny]
    serializer_class = TopicSerializer
    queryset = Topic.objects.all()
    lookup_field = "slug"  # использую это потому что у модели есть поле slug и это удобно для человекочитаемых URL


class SpecialisationListView(generics.ListAPIView):
    """Класс-контроллер на основе Generic для получения списка всех Specialisations.
    Используется, например, при выборе специализации (методологичесая школа) в профиле психолога."""

    permission_classes = [AllowAny]
    serializer_class = SpecialisationSerializer
    queryset = Specialisation.objects.all().order_by("name")


class SpecialisationDetailView(generics.RetrieveAPIView):
    """Класс-контроллер на основе Generic для получения подробной информации о Specialisation (методологическая школа).
    Поиск записи выполняется по полю slug (человекочитаемый URL)."""

    permission_classes = [AllowAny]
    serializer_class = SpecialisationSerializer
    queryset = Specialisation.objects.all()
    lookup_field = "slug"  # использую это потому что у модели есть поле slug и это удобно для человекочитаемых URL


class MethodListView(generics.ListAPIView):
    """Класс-контроллер на основе Generic для получения списка всех Methods (инструмент/подход).
    Используется, например, при выборе метода в профиле клиента/психолога."""

    permission_classes = [AllowAny]
    serializer_class = MethodSerializer
    queryset = Method.objects.all().order_by("name")


class MethodDetailView(generics.RetrieveAPIView):
    """Класс-контроллер на основе Generic для получения подробной информации о Method.
    Поиск записи выполняется по полю slug (человекочитаемый URL)."""

    permission_classes = [AllowAny]
    serializer_class = MethodSerializer
    queryset = Method.objects.all()
    lookup_field = "slug"  # использую это потому что у модели есть поле slug и это удобно для человекочитаемых URL


class EducationListCreateView(generics.ListCreateAPIView):
    """Класс-контроллер на основе Generic для:
        - создания новой записи в Education;
        - получения списка всех Educations."""

    permission_classes = [IsAuthenticated]
    serializer_class = EducationSerializer

    def get_queryset(self):
        """Пользователь может видеть только свои образования.
        Исключение: Администраторы могут видеть все записи в БД."""
        user = self.request.user

        if user.is_staff:
            return Education.objects.all().order_by("creator__email", "-year_start")
        return Education.objects.filter(creator=user).order_by("-year_start")


class EducationRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Класс-контроллер на основе Generic для работы с одним конкретным Education:
        - получение подробной информации;
        - редактирование;
        - удаление."""

    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = EducationSerializer

    def get_queryset(self):
        """Администратор может работать со всеми записями. Обычный пользователь - только со своими."""
        user = self.request.user

        if user.is_staff:
            return Education.objects.all()
        return Education.objects.filter(creator=user)


# =====
# AJAX-ЗАПРОСЫ (fetch)
# =====

class SavePreferredTopicTypeAjaxView(LoginRequiredMixin, IsProfileOwnerOrAdminMixin, View):
    """Класс-контроллер на основе View для автосохранения без кнопки "Сохранить", как это делают
    профессиональные SaaS-сервисы. Решение: AJAX-запрос (fetch) на специальный API-endpoint.
    Моментальное сохранение выбранного клиентом значения в preferred_topic_type на html-страницах."""

    def post(self, request, *args, **kwargs):
        """Сохранение значения в preferred_topic_type."""
        value = request.POST.get("preferred_topic_type")  # получаем значение в has_preferences с html-страницы

        if value not in dict(PREFERRED_TOPIC_TYPE_CHOICES):  # проверяем что значение соответствует справочнику
            return JsonResponse(
                data={"status": "error", "error": "invalid_value"}, status=400
            )

        profile = request.user.client_profile
        profile.preferred_topic_type = value
        profile.save(update_fields=["preferred_topic_type"])

        return JsonResponse(
            data={"status": "ok", "saved": value}, status=200
        )


class SaveRequestedTopicsAjaxView(LoginRequiredMixin, IsProfileOwnerOrAdminMixin, View):
    """Класс-контроллер на основе View для автосохранения чекбоксов без кнопки "Сохранить", как это делают
    профессиональные SaaS-сервисы. Решение: AJAX-запрос (fetch) на специальный API-endpoint.

    Моментальное сохранение выбранных клиентом тем в requested_topics на html-страницах:
        - когда пользователь ставит или убирает галочку;
        - чтобы при переходе по навигации (со страницы на страницу) данные не терялись;
        - чтобы страница подгружалась уже с сохранившимися значениями."""

    def post(self, request, *args, **kwargs):
        """Сохранение выбранных методов в requested_topics."""
        profile = request.user.client_profile
        ids = request.POST.getlist("topics[]")  # получаем список ID

        profile.requested_topics.set(ids)
        profile.save()

        return JsonResponse(
            data={"status": "ok", "saved": ids}, status=200
        )


class SaveHasPreferencesAjaxView(LoginRequiredMixin, IsProfileOwnerOrAdminMixin, View):
    """Класс-контроллер на основе View для автосохранения без кнопки "Сохранить", как это делают
    профессиональные SaaS-сервисы. Решение: AJAX-запрос (fetch) на специальный API-endpoint.
    Моментальное сохранение выбранного клиентом значения в has_preferences на html-страницах."""

    def post(self, request, *args, **kwargs):
        """Сохранение значения в has_preferences."""
        value = request.POST.get("has_preferences")  # получаем значение в has_preferences с html-страницы

        if value not in ("0", "1"):  # проверяем что это bool
            return JsonResponse(
                data={"status": "error", "error": "invalid_value"}, status=400
            )

        # Это профессиональный Python-паттерн: "= (value == "1")" возвращает значение True или False:
        has_pref = (value == "1")

        profile = request.user.client_profile
        profile.has_preferences = has_pref
        profile.save(update_fields=["has_preferences"])

        return JsonResponse(
            data={"status": "ok", "saved": has_pref}, status=200
        )


class SavePreferredGenderAjaxView(LoginRequiredMixin, IsProfileOwnerOrAdminMixin, View):
    """Класс-контроллер на основе View для автосохранения без кнопки "Сохранить", как это делают
    профессиональные SaaS-сервисы. Решение: AJAX-запрос (fetch) на специальный API-endpoint.
    Моментальное сохранение выбранного клиентом значения в preferred_ps_gender на html-страницах."""

    def post(self, request, *args, **kwargs):
        """Сохранение значения в preferred_ps_gender."""
        # получаем список в preferred_ps_gender со страницы (нормализация values=[... if v] - страхует от пустых строк)
        values = [v for v in request.POST.getlist("preferred_ps_gender") if v]

        # валидация (issubset - идеален для валидации списков)
        valid_values = set(dict(GENDER_CHOICES))
        if any(value not in valid_values for value in values):
            return JsonResponse(
                data={"status": "error", "error": "invalid_value"}, status=400
            )

        profile = request.user.client_profile
        profile.preferred_ps_gender = values
        profile.save(update_fields=["preferred_ps_gender"])

        return JsonResponse(
            data={"status": "ok", "saved": values}, status=200
        )


class SavePreferredAgeAjaxView(LoginRequiredMixin, IsProfileOwnerOrAdminMixin, View):
    """Класс-контроллер на основе View для автосохранения без кнопки "Сохранить", как это делают
    профессиональные SaaS-сервисы. Решение: AJAX-запрос (fetch) на специальный API-endpoint.
    Моментальное сохранение выбранного клиентом значения в preferred_ps_age на html-страницах."""

    def post(self, request, *args, **kwargs):
        """Сохранение значения в preferred_ps_age."""
        # получаем список в preferred_ps_age со страницы (нормализация values=[... if v] - страхует от пустых строк)
        values = [v for v in request.POST.getlist("preferred_ps_age") if v]

        # валидация (issubset - идеален для валидации списков)
        valid_values = set(dict(AGE_BUCKET_CHOICES))
        if any(value not in valid_values for value in values):
            return JsonResponse(
                data={"status": "error", "error": "invalid_value"}, status=400
            )

        profile = request.user.client_profile
        profile.preferred_ps_age = values
        profile.save(update_fields=["preferred_ps_age"])

        return JsonResponse(
            data={"status": "ok", "saved": values}, status=200
        )


class SavePreferredMethodsAjaxView(LoginRequiredMixin, IsProfileOwnerOrAdminMixin, View):
    """Класс-контроллер на основе View для автосохранения чекбоксов без кнопки "Сохранить", как это делают
    профессиональные SaaS-сервисы. Решение: AJAX-запрос (fetch) на специальный API-endpoint.

    Моментальное сохранение выбранных клиентом методов в preferred_methods на html-страницах:
        - когда пользователь ставит или убирает галочку;
        - чтобы при переходе по навигации (со страницы на страницу) данные не терялись;
        - чтобы страница подгружалась уже с сохранившимися значениями."""

    def post(self, request, *args, **kwargs):
        """Сохранение выбранных методов в preferred_methods."""
        profile = request.user.client_profile
        ids = request.POST.getlist("methods[]")  # получаем список ID

        profile.preferred_methods.set(ids)
        profile.save()

        return JsonResponse(
            data={"status": "ok", "saved": ids}, status=200
        )


class SaveHasTimePreferencesAjaxView(LoginRequiredMixin, IsProfileOwnerOrAdminMixin, View):
    """Класс-контроллер на основе View для автосохранения без кнопки "Сохранить", как это делают
    профессиональные SaaS-сервисы. Решение: AJAX-запрос (fetch) на специальный API-endpoint.
    Моментальное сохранение выбранного клиентом значения в has_time_preferences на html-страницах."""

    def post(self, request, *args, **kwargs):
        """Сохранение значения в has_time_preferences."""
        value = request.POST.get("has_time_preferences")  # получаем значение в has_time_preferences с html-страницы

        if value not in ["1", "0"]:  # проверяем что это bool
            return JsonResponse(
                data={"status": "error", "error": "invalid_value"}, status=400
            )

        # Это профессиональный Python-паттерн: "= (value == "1")" возвращает значение True или False:
        has_pref = (value == "1")

        profile = request.user.client_profile
        profile.has_time_preferences = has_pref
        profile.save(update_fields=["has_time_preferences"])

        return JsonResponse(
            data={"status": "ok", "saved": has_pref}, status=200
        )


class SavePreferredSlotsAjaxView(LoginRequiredMixin, IsProfileOwnerOrAdminMixin, View):
    """Класс-контроллер на основе View для автосохранения без кнопки "Сохранить", как это делают
    профессиональные SaaS-сервисы. Решение: AJAX-запрос (fetch) на специальный API-endpoint.
    Моментальное сохранение выбранных клиентом значений в preferred_slots на html-страницах."""

    def post(self, request, *args, **kwargs):
        """Сохранение значения в preferred_slots."""
        slot_values = request.POST.getlist("slots[]")  # Получаем из запроса значения в slot

        # допустимо: пользователь снял все слоты
        if not slot_values:
            profile = request.user.client_profile
            profile.preferred_slots = []
            profile.save(update_fields=["preferred_slots"])
            return JsonResponse(
                data={"status": "ok", "slots_count": 0}, status=200,
            )

        slots = []

        for value in slot_values:
            # Далее превращаю строку в дату.
            # parse_datetime - магическая функция, которая понимает формат и превращает "2026-01-15" в объект Python
            slot_dt = parse_datetime(value)

            if not slot_dt:
                return JsonResponse(
                    data={"status": "error", "error": "invalid_datetime"}, status=400,
                )

            if is_naive(slot_dt):
                slot_dt = make_aware(slot_dt)

            slot_dt = slot_dt.replace(minute=0, second=0, microsecond=0)

            # Нельзя бронировать время, которое уже прошло. Мы сравниваем присланное время с текущим моментом - now().
            # У нас изначально планируется отображение на странице слотов текущего дня + ближайшие дни и отображать
            # прошло не планируется, но лучше добавить эту проверку, хоть она и может показаться лишней
            if slot_dt < now():
                return JsonResponse(
                    data={"status": "error", "error": "slot_in_past"}, status=400,
                )

            slots.append(slot_dt)

        profile = request.user.client_profile
        profile.preferred_slots = slots
        profile.save(update_fields=["preferred_slots"])

        return JsonResponse(
            data={"status": "ok", "slots_count": len(slots)}, status=200,
        )


class GetDomainSlotsAjaxView(LoginRequiredMixin, View):
    """Возвращает клиенту на UI все возможные доменные временные слоты (общее правило домена).
    Read-only эндпоинт только для показа возможных слотов на странице пользователя, без сохранения в БД."""

    def get(self, request, *args, **kwargs):
        """Получить все доменные временные слоты."""
        user = request.user
        profile = user.client_profile

        use_case = GetDomainSlotsUseCase(
            timezone=user.timezone
        )

        result = use_case.execute()

        # ВАЖНО: кроме сгенерированных слотов (slots) нам необходимо передать на фронт еще текущее время
        # пользователя (now_iso), потому что определять его по времени сервера неправильно. Так как клиент в
        # настройках своего профиля указывает свой timezone и он может отличаться от сервера (путешествует например).
        # ОБОСНОВАНИЕ: текущее время пользователя нам необходимо для того, чтоб потом на странице деактивировать
        # слоты, которые уже в прошлом (делать их недоступными к выбору).
        return JsonResponse(
            data={
                "status": "ok",
                "now_iso": result["now_iso"],
                "slots": result["slots"],
            },
            status=200,
        )


class GetSpecialistScheduleAjaxView(LoginRequiredMixin, View):
    """Возвращает клиенту на UI в карточке конкретного специалиста актуальное расписание данного специалиста:
        - ближайший доступный слот;
        - все доступные слоты в блоке "Расписание".
    Все слоты ОТОБРАЖЕНЫ в TZ КЛИЕНТА.
    Read-only эндпоинт только для показа доступных слотов из расписания специалиста, без сохранения в БД."""

    def get(self, request, *args, **kwargs):
        """Получить расписание специалиста (доступные слоты) в TZ клиента."""
        user = request.user
        profile_id = kwargs["profile_id"]
        # Эта вьюха берет profile_id из kwargs и далее использует specialist_profile.user, поэтому нужно
        # использовать get_object_or_404() и передавать именно объект дальше.
        specialist_profile = get_object_or_404(PsychologistProfile, pk=profile_id)

        def normalize_tz(tz_value):
            """Безопасный fallback на 'timezone=None'.
            Просто 'ZoneInfo(str(specialist_profile.user.timezone))' превратит None в 'None' и выбросит исключение.
            Поэтому нужна безопасная ветка: если timezone None - fallback на now() без astimezone."""
            if tz_value is None:
                return None
            if isinstance(tz_value, tzinfo):
                return tz_value
            return ZoneInfo(str(tz_value))

        client_tz = normalize_tz(getattr(user, "timezone", None))
        specialist_tz = normalize_tz(getattr(specialist_profile.user, "timezone", None)) or client_tz

        use_case = build_generate_specialist_schedule_use_case(
            specialist_profile=specialist_profile,
        )

        if use_case is None:
            return JsonResponse(
                {
                    "status": "ok",
                    "nearest_slot": None,
                    "schedule": [],
                },
                status=200,
            )

        slots = use_case.execute()

        # ВАЖНО: кроме сгенерированного расписания нам необходимо передать на фронт еще текущее время
        # клиента (now_iso_client) и текущее время специалиста (now_iso_specialist), потому что определять
        # его по времени сервера неправильно. Так как клиент/специалист в настройках своего профиля
        # указывает свой timezone и он может отличаться от сервера (путешествует например).
        # ОБОСНОВАНИЕ: полезно для отладки и тестирования.
        now_client = now().astimezone(client_tz) if client_tz else now()
        now_specialist = now().astimezone(specialist_tz) if specialist_tz else now()

        # Use-case генерирует слоты в TZ специалиста, но ответ должен быть в TZ клиента.
        # Изначально отправляется raw SlotDTO, так что клиент увидит время специалиста.
        # Нужна конвертация: локализовать (day+start_time) в TZ специалиста и перевести в TZ клиента,
        # затем отдать ISO/строку.
        schedule = []

        for slot in slots:
            if specialist_tz:
                slot_start_spec = datetime.combine(slot.day, slot.start, tzinfo=specialist_tz)
                slot_end_spec = datetime.combine(slot.day, slot.end, tzinfo=specialist_tz)
            else:
                slot_start_spec = datetime.combine(slot.day, slot.start)
                slot_end_spec = datetime.combine(slot.day, slot.end)

            if slot_start_spec < now_specialist:
                continue

            slot_start_client = (
                slot_start_spec.astimezone(client_tz)
                if client_tz
                else slot_start_spec
            )
            slot_end_client = (
                slot_end_spec.astimezone(client_tz)
                if client_tz
                else slot_end_spec
            )

            # schedule возвращает как SlotDTO, который не JSON‑serializable поэтому нужен перевод в ISO datetime
            schedule.append(
                {
                    "day": slot_start_client.date().isoformat(),
                    "start_time": slot_start_client.strftime("%H:%M"),
                    "end_time": slot_end_client.strftime("%H:%M"),
                    "start_iso": slot_start_client.isoformat(),
                    "end_iso": slot_end_client.isoformat(),
                }
            )

        nearest_slot = schedule[0] if schedule else None

        return JsonResponse(
            {
                "status": "ok",
                "now_iso_client": now_client.isoformat(),
                "now_iso_specialist": now_specialist.isoformat(),
                "nearest_slot": nearest_slot,
                "schedule": schedule,
            },
            status=200,
        )
