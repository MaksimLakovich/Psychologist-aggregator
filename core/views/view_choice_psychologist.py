from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView

from core.forms.form_choice_psychologist import ClientChoicePsychologistForm


class ClientChoicePsychologistPageView(LoginRequiredMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Выбор психолога*."""

    template_name = "core/client_pages/home_client_choice_psychologist.html"
    form_class = ClientChoicePsychologistForm
    success_url = reverse_lazy("core:choice-psychologist")  # TODO: Заменить позже, когда создам след страницу
