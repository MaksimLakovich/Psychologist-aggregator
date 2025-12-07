from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

# ------
# Permission-классы для DRF:
# ------


class IsOwnerOrAdmin(BasePermission):
    """Кастомный DRF permission-класс, который разрешает доступ если:
        - пользователь является владельцем объекта;
        - пользователь является действующим админом.
    Используется для Education-эндпоинтов, где есть поле creator и необходимо использовать 'obj.creator == user'."""

    message = "У вас нет прав на действия с данной записью."

    def has_object_permission(self, request, view, obj):
        """Возвращает True, если пользователь является владельцем объекта ИЛИ действующим админом."""
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Булево выражение (в виде логической цепочки). Оно возвращает True, только если все условия истинны
        return (
            obj.creator == user
            or (user.is_staff and user.is_active)
        )


class IsSelfOrAdmin(BasePermission):
    """Кастомный DRF permission-класс, который разрешает доступ если:
        - объект AppUser равен request.user (владение);
        - пользователь является действующим админом.
    Используется для AppUser-эндпоинтов (там нет поля creator поэтому работаем с 'obj == user')."""

    message = "У вас нет прав на доступ к этому аккаунту."

    def has_object_permission(self, request, view, obj):
        """Возвращает True, если пользователь является владельцем объекта ИЛИ действующим админом."""
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return (
            obj == user
            or (user.is_staff and user.is_active)
        )


class IsProfileOwnerOrAdmin(BasePermission):
    """Кастомный DRF permission-класс, который разрешает доступ если:
        - профиль (объект PsychologistProfile) принадлежит текущему пользователю;
        - пользователь является действующим админом.
    Используется для PsychologistProfile-эндпоинтов (там нет поля creator поэтому работаем с 'obj.user == user')."""

    message = "У вас нет прав на доступ к этому профилю."

    def has_object_permission(self, request, view, obj):
        """Возвращает True, если пользователь является владельцем объекта ИЛИ действующим админом."""
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return (
            obj.user == user
            or (user.is_staff and user.is_active)
        )


# ------
# Permission-классы для CBV:
# ------


class IsProfileOwnerOrAdminMixin:
    """Кастомный DRF permission-класс (mixin для Django CBV). Проверяет, что:
        - пользователь это владелец ClientProfile;
        - пользователь является действующим админом."""

    def dispatch(self, request, *args, **kwargs):
        """Метод для проверки прав или выполнения общих проверок перед выполнением GET/POST."""
        user = request.user

        if not user.is_authenticated:
            raise PermissionDenied("Вы не авторизованы.")

        profile = getattr(user, "client_profile", None)

        if profile is None:
            raise PermissionDenied("У вас нет клиентского профиля.")

        # Проверка: владелец или админ
        if profile.user != user and not (user.is_staff and user.is_active):
            raise PermissionDenied("У вас нет прав на доступ к этому профилю.")

        return super().dispatch(request, *args, **kwargs)


# class IsModerator(BasePermission):
#     """Кастомный permission-класс, проверяющий, является ли пользователь модератором. Модераторы - это пользователи,
#     которые входят в группу "Moderators". Им разрешается просматривать (GET) и редактировать (PUT, PATCH) объекты,
#     но не создавать (POST) и не удалять (DELETE)."""
#
#     def has_permission(self, request, view):
#         """Возвращает True, если пользователь аутентифицирован и состоит в группе "Moderators".
#         Используется в контроллерах для ограничения доступа к операциям создания и удаления."""
#
#         return (
#             request.user.is_authenticated
#             and request.user.groups.filter(name="Moderators").exists()
#         )
