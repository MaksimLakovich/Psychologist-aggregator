from rest_framework.permissions import BasePermission


class IsOwnerOrAdmin(BasePermission):
    """Кастомный permission-класс, который разрешает доступ если:
        - пользователь является владельцем объекта;
        - пользователь является действующим админом.
    Используется для Education-эндпоинтов."""

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
    """Кастомный permission-класс, который разрешает доступ если:
        - объект AppUser равен request.user (владение);
        - пользователь является действующим админом.
    Используется для AppUser-эндпоинтов (там нет поля Creator поэтому работаем с "obj == user")."""

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


# class IsActiveAdmin(BasePermission):
#     """Кастомный permission-класс, который разрешает доступ только действующим админам (is_active + is_staff)."""
#
#     message = "У вас нет прав на действия с данной записью."
#
#     def has_permission(self, request, view):
#         """Возвращает True, если пользователь активен и является админом.
#         Используется во views для предоставления доступа админам к операциям CRUD над объектами."""
#         user = request.user
#
#         # Булево выражение (в виде логической цепочки). Оно возвращает True, только если все условия истинны
#         return (
#             user
#             and user.is_authenticated
#             and user.is_staff
#             and user.is_active
#         )
#
#
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
