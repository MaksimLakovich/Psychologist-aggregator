from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from users.constants import ALLOWED_REGISTER_ROLES
from users.models import UserRole
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
