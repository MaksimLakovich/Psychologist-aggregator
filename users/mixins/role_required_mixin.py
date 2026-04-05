from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class RoleRequiredMixin(AccessMixin):
    """Базовый mixin для доступов на основе role в обычных Django CBV.

    - allowed_roles: это список ролей, которым страница разрешен;
    - allow_anonymous: можно ли открывать страницу гостю, без логина;
    - allow_staff: разрешать ли staff/superuser проходить проверку даже если роль не совпала;
    - role_denied_redirect_url: куда отправить авторизованного пользователя, если он вошел, но роль не подходит:
        - если None, будет ошибка PermissionDenied;
        - если задан route name, будет redirect.
    - permission_denied_message: текст ошибки, если мы выбрали не redirect, а 403 PermissionDenied.
    """

    ROLE_HOME_URLS = {
        "client": "core:start-page",
        "psychologist": "core:psychologist-account",
        "admin": "core:start-page",
    }

    allowed_roles: tuple[str, ...] = ()
    allow_anonymous = False
    allow_staff = True
    role_denied_redirect_url: str | None = None
    default_role_denied_redirect_url = "core:start-page"
    permission_denied_message = "У вас нет доступа к этой странице!"

    def get_allowed_roles(self) -> tuple[str, ...]:
        """Возвращает набор разрешенных ролей для конкретной view.
        Сделан отдельным методом, чтобы позже при желании можно было переопределить логику динамически."""
        return tuple(self.allowed_roles)

    def get_user_role_value(self) -> str | None:
        """Безопасно достает текстовое значение роли пользователя.
        Т.е., берет из пользователя текст роли: client или psychologist."""
        role_obj = getattr(self.request.user, "role", None)
        return getattr(role_obj, "role", None)

    def has_staff_bypass(self) -> bool:
        """Проверяет и разрешает активному staff/admin обходить role-проверку при необходимости."""
        user = self.request.user
        return bool(
            self.allow_staff
            and user.is_authenticated
            and user.is_active
            and (user.is_staff or user.is_superuser)
        )

    def has_allowed_role(self) -> bool:
        """Проверяет, входит ли роль текущего пользователя в белый список view."""
        return self.get_user_role_value() in self.get_allowed_roles()

    def get_role_denied_redirect_url(self) -> str | None:
        """Возвращает URL для редиректа при заходе с неподходящей ролью.
        Приоритет:
            1) Явный override на уровне конкретного mixin/view через role_denied_redirect_url.
            2) "Домашняя" страница текущей роли из ROLE_HOME_URLS.
            3) Общий fallback default_role_denied_redirect_url.
        """
        if self.role_denied_redirect_url:
            return self.role_denied_redirect_url

        role_value = self.get_user_role_value()
        if role_value in self.ROLE_HOME_URLS:
            return self.ROLE_HOME_URLS[role_value]

        return self.default_role_denied_redirect_url

    def handle_authenticated_role_mismatch(self):
        """Срабатывает, когда пользователь уже залогинен, но роль не подходит.
        Тут решается: либо redirect, либо PermissionDenied."""
        redirect_url = self.get_role_denied_redirect_url()
        if redirect_url:
            return redirect(redirect_url)
        raise PermissionDenied(self.get_permission_denied_message())

    def check_role_access(self, request):
        """Это центральный метод: проверяет доступ и возвращает HttpResponse только если доступ запрещен:
        - если пользователь гость:
            - если allow_anonymous=True, пускаем;
            - иначе вызываем стандартный handle_no_permission() из AccessMixin
        - если пользователь авторизован:
            - если staff_bypass, пускаем;
            - если роль подходит, пускаем;
            - иначе redirect/403
        """
        if not request.user.is_authenticated:
            if self.allow_anonymous:
                return None
            return self.handle_no_permission()

        if self.has_staff_bypass() or self.has_allowed_role():
            return None

        return self.handle_authenticated_role_mismatch()

    def dispatch(self, request, *args, **kwargs):
        """Это входная точка Django CBV.
            - она срабатывает раньше get(), post(), get_context_data() и т.д.;
            - т.е., сначала идет проверка роли, и только потом выполняется сама view.
        """
        access_response = self.check_role_access(request)
        if access_response is not None:
            return access_response
        return super().dispatch(request, *args, **kwargs)


class ClientRequiredMixin(RoleRequiredMixin):
    """Разрешает доступ только клиенту, при этом может опционально пускать гостя."""

    allowed_roles = ("client",)
    permission_denied_message = "Страница доступна только пользователям с ролью клиента."


class PsychologistRequiredMixin(RoleRequiredMixin):
    """Разрешает доступ только психологу."""

    allowed_roles = ("psychologist",)
    permission_denied_message = "Страница доступна только пользователям с ролью психолога."
