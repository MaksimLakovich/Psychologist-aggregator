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
from users.serializers import (CustomTokenObtainPairSerializer,
                               RegisterSerializer)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Класс-контроллер на основе TokenObtainPairView для авторизации по email."""

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]  # type: ignore[assignment]


class RegisterView(generics.GenericAPIView):
    """Класс-контроллер на основе базового GenericAPIView для регистрации:
     1) Нового пользователя с профилем 'Психолог', если параметр role = psychologist.
     2) Нового пользователя с профилем 'Клиент', если параметр role = client."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]  # type: ignore[assignment]

    def post(self, request, *args, **kwargs):
        """Метод для создания нового пользователя и связанного профиля
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

        return Response(data=serializer.data, status=status.HTTP_201_CREATED)


class EmailVerificationView(APIView):
    """Класс-контроллер на основе APIView для подтверждения email и активации пользователя после регистрации."""

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        """Метод для:
            1) Генерация ссылки с токеном после успешной регистрации;
            2) Отправка письма с этой ссылкой;
            3) Прием токена, его валидация и активация пользователя."""
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
