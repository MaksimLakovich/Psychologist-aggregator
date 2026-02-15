from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect


class AnonymousOnlyMixin(AccessMixin):
    """Миксин, который ограничивает доступ к форме/странице только для неавторизованных пользователей.
    Авторизованные пользователи не могут открыть страницу и перенаправляются на указанную в настройках."""

    def dispatch(self, request, *args, **kwargs):
        """Если пользователь уже авторизован - перенаправляем его."""
        if request.user.is_authenticated:
            return redirect("core:start-page")
        return super().dispatch(request, *args, **kwargs)
