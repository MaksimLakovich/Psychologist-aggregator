from django.views.generic import TemplateView

from users.mixins.role_required_mixin import PsychologistRequiredMixin


class PsychologistAccountStubPageView(PsychologistRequiredMixin, TemplateView):
    """Временная стартовая страница кабинета психолога до реализации полного psychologist-flow."""

    template_name = "core/psychologist_pages/account_stub.html"

    def get_context_data(self, **kwargs):
        """Формирует контекст временной заглушки кабинета психолога."""
        context = super().get_context_data(**kwargs)
        context["title_psychologist_account_view"] = "Кабинет специалиста в сервисе ОПОРА"
        context["current_sidebar_key"] = "psychologist-account"

        return context
