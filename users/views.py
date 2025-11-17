from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from users.constants import ALLOWED_REGISTER_ROLES
from users.models import AppUser, UserRole
from users.serializers import (ChangePasswordSerializer,
                               CustomTokenObtainPairSerializer,
                               LogoutSerializer, RegisterSerializer)
from users.services.send_verification_email import send_verification_email
from users.services.throttles import ChangePasswordThrottle, ResendThrottle


class CustomTokenObtainPairView(TokenObtainPairView):
    """Класс-контроллер на основе TokenObtainPairView для авторизации по email."""

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]  # type: ignore[assignment]


class LogoutAPIView(APIView):
    """Класс-контроллер на основе APIView для реального выхода пользователя из системы.
    Добавляет его refresh токен в blacklist, делая невозможным дальнейшее обновление access токена."""

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


class RegisterView(generics.GenericAPIView):
    """Класс-контроллер на основе базового GenericAPIView для регистрации:
     1) Нового пользователя с профилем 'Психолог', если параметр role = psychologist.
     2) Нового пользователя с профилем 'Клиент', если параметр role = client."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]  # type: ignore[assignment]
    throttle_classes = [ResendThrottle]  # Добавляю throttle (anti-spam) для отправки email на подтверждение активации

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


class ResendEmailVerificationView(APIView):
    """Класс-контроллер на основе APIView для запроса на повторное подтверждения email и активации пользователя
    после регистрации (если предыдущее не было использовано)."""

    permission_classes = [AllowAny]
    throttle_classes = [ResendThrottle]  # Добавляю throttle (anti-spam) для отправки email на подтверждение активации

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
