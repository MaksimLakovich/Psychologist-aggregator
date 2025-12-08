from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.http import JsonResponse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import (BlacklistedToken,
                                                             OutstandingToken)
from rest_framework_simplejwt.views import TokenObtainPairView

from users._api.serializers import (AppUserSerializer,
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
from users.constants import (ALLOWED_REGISTER_ROLES,
                             PREFERRED_TOPIC_TYPE_CHOICES)
from users.models import (AppUser, ClientProfile, Education, Method,
                          PsychologistProfile, Specialisation, Topic, UserRole)
from users.permissions import (IsOwnerOrAdmin, IsProfileOwnerOrAdmin,
                               IsProfileOwnerOrAdminMixin, IsSelfOrAdmin)
from users.services.send_password_reset_email import send_password_reset_email
from users.services.send_verification_email import send_verification_email
from users.services.throttles import (ChangePasswordThrottle, LoginThrottle,
                                      PasswordResetConfirmThrottle,
                                      PasswordResetThrottle, RegisterThrottle,
                                      ResendThrottle)


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
