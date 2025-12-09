from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from core.forms.form_personal_questions import ClientPersonalQuestionsForm
from users.models import ClientProfile, Method, Topic


class ClientPersonalQuestionsPageView(LoginRequiredMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Персональные вопросы* - предпочтения клиента."""

    template_name = "core/client_pages/home_client_personal_questions.html"
    form_class = ClientPersonalQuestionsForm
    success_url = reverse_lazy("core:client_personal_questions_page")  # TODO: заменить позже

    def get_initial(self):
        """Возвращает предзаполненные значения формы, полученные из ClientProfile по данным:
            - preferred_topic_type;
            - requested_topics;
            - has_preferences;
            - preferred_methods.
        Вызывается автоматически FormView при создании формы."""
        initial = super().get_initial()
        user = self.request.user
        profile = get_object_or_404(ClientProfile, user=user)

        # 1) preferred_topic_type
        initial["preferred_topic_type"] = profile.preferred_topic_type

        # 2) requested_topics
        try:
            selected = profile.requested_topics.values_list("id", flat=True)
            initial["requested_topics"] = list(selected)
        except Exception:
            initial["requested_topics"] = []

        # 3) has_preferences
        initial["has_preferences"] = profile.has_preferences

        # 4) preferred_methods
        try:
            selected = profile.preferred_methods.values_list("id", flat=True)
            initial["preferred_methods"] = list(selected)
        except Exception:
            initial["preferred_methods"] = []

        return initial

    def _group_topics(self):
        """Группируем темы по type и внутри по group_name.
            Структура:
            {
                "Индивидуальная": {
                    "group_name": [Topic, Topic],
                    "group_name": [...],
                },
                "Парная": {
                    ...
                }
            }
        """
        topics = Topic.objects.all().order_by("type", "group_name", "name")

        result = {
            "Индивидуальная": {},
            "Парная": {}
        }

        for topic in topics:
            bucket = result[topic.type]
            bucket.setdefault(topic.group_name, [])
            bucket[topic.group_name].append(topic)

        return result

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в HTML-шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) Возвращает:
        - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)

        form = context["form"]

        # 1) preferred_topic_type
        context["preferred_topic_type"] = form.initial.get("preferred_topic_type", "individual")

        # 2) requested_topics: 1) группируем; 2) превращаем PK тем в строки, чтобы удобнее работать в JS
        context["topics_by_type"] = self._group_topics()
        context["selected_topics"] = [
            str(pk) for pk in form.initial.get("requested_topics", [])
        ]

        # 3) has_preferences
        context["has_preferences"] = form.initial.get("has_preferences", False)

        # 4) preferred_methods (для шаблона превращаем PK методов в строки, чтобы удобнее работать в JS)
        context["methods"] = Method.objects.all().order_by("name")
        context["selected_methods"] = [
            str(pk) for pk in form.initial.get("preferred_methods", [])
        ]

        context["title_home_page_view"] = "Психологи онлайн на Опора — поиск и подбор психолога"

        return context

    def form_valid(self, form):
        """Сохраняем изменения в профиле (fallback-сохранение, если AJAX не сработал)."""
        profile = get_object_or_404(ClientProfile, user=self.request.user)

        # 1) preferred_topic_type
        profile.preferred_topic_type = form.cleaned_data.get("preferred_topic_type")

        # 2) requested_topics
        selected_topics = form.cleaned_data["requested_topics"]
        profile.requested_topics.set(selected_topics)

        # 2) has_preferences
        profile.has_preferences = form.cleaned_data.get("has_preferences", False)

        # 3) preferred_methods
        selected_methods = form.cleaned_data["preferred_methods"]
        profile.preferred_methods.set(selected_methods)

        profile.save()

        return super().form_valid(form)
