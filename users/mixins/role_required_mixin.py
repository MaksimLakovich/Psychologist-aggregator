from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class RoleRequiredMixin(AccessMixin):
    """Базовый mixin для доступов на основе role в обычных Django CBV."""

    allowed_roles: tuple[str, ...] = ()
    allow_anonymous = False
    allow_staff = True
    role_denied_redirect_url: str | None = None
    permission_denied_message = "У вас нет доступа к этой странице!"

    def get_allowed_roles(self) -> tuple[str, ...]:
        """Возвращает набор разрешенных ролей для конкретной view."""
        return tuple(self.allowed_roles)

    def get_user_role_value(self) -> str | None:
        """Безопасно достает текстовое значение роли пользователя."""
        role_obj = getattr(self.request.user, "role", None)
        return getattr(role_obj, "role", None)

    def has_staff_bypass(self) -> bool:
        """Разрешает активному staff/admin обходить role-проверку при необходимости."""
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
        """Возвращает URL/route-name для редиректа при заходе с неподходящей ролью."""
        return self.role_denied_redirect_url

    def handle_authenticated_role_mismatch(self):
        """Обрабатывает попытку доступа авторизованного пользователя с неподходящей ролью."""
        redirect_url = self.get_role_denied_redirect_url()
        if redirect_url:
            return redirect(redirect_url)
        raise PermissionDenied(self.get_permission_denied_message())

    def check_role_access(self, request):
        """Проверяет доступ и возвращает HttpResponse только если доступ запрещен."""
        if not request.user.is_authenticated:
            if self.allow_anonymous:
                return None
            return self.handle_no_permission()

        if self.has_staff_bypass() or self.has_allowed_role():
            return None

        return self.handle_authenticated_role_mismatch()

    def dispatch(self, request, *args, **kwargs):
        """Выполняет role-check до основной логики view."""
        access_response = self.check_role_access(request)
        if access_response is not None:
            return access_response
        return super().dispatch(request, *args, **kwargs)


class ClientRequiredMixin(RoleRequiredMixin):
    """Разрешает доступ только клиенту, при этом может опционально пускать гостя."""

    allowed_roles = ("client",)
    role_denied_redirect_url = "core:psychologist-account"
    permission_denied_message = "Страница доступна только пользователям с ролью клиента."


class PsychologistRequiredMixin(RoleRequiredMixin):
    """Разрешает доступ только психологу."""

    allowed_roles = ("psychologist",)
    role_denied_redirect_url = "core:start-page"
    permission_denied_message = "Страница доступна только пользователям с ролью психолога."
