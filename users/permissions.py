from rest_framework.permissions import BasePermission


class IsOwnerOrAdmin(BasePermission):
    """Кастомный permission-класс, который разрешает доступ если 'пользователь является владельцем объекта'
    ИЛИ 'пользователь является действующим админом'."""

    message = "У вас нет прав на действия с данной записью."

    def has_object_permission(self, request, view, obj):
        """Возвращает True, если пользователь является владельцем объекта ИЛИ действующим админом."""
        user = request.user

        # Булево выражение (в виде логической цепочки). Оно возвращает True, только если все условия истинны
        return (
            obj.creator == user
            or (user.is_authenticated and user.is_staff and user.is_active)
        )


# class IsOwner(BasePermission):
#     """Кастомный permission-класс, который разрешает доступ только владельцу объекта."""
#
#     message = "У вас нет прав на действия с данной записью."
#
#     def has_object_permission(self, request, view, obj):
#         """Возвращает True, если пользователь является владельцем объекта.
#         Используется во views для ограничения доступа к операциям с чужими объектами."""
#         return obj.creator == request.user  # Булево выражение
#
#
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
