from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.edit import FormView

from core.forms.client.specialist_matching.form_personal_questions import \
    ClientPersonalQuestionsForm
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin
from core.services.topic_groups import build_topics_grouped_by_type
from users.models import ClientProfile, Method


class ClientPersonalQuestionsPageView(SpecialistMatchingLayoutMixin, LoginRequiredMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Персональные вопросы* - предпочтения клиента."""

    template_name = "core/client_pages/specialist_matching/home_client_personal_questions.html"
    form_class = ClientPersonalQuestionsForm

    def get_initial(self):
        """Возвращает предзаполненные значения формы, полученные из ClientProfile по данным:
            - preferred_topic_type;
            - requested_topics;
            - has_preferences;
            - preferred_ps_gender;
            - preferred_ps_age;
            - preferred_methods;
            - has_time_preferences
            - preferred_slots.
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

        # 4) preferred_ps_gender
        initial["preferred_ps_gender"] = profile.preferred_ps_gender

        # 5) preferred_ps_age
        initial["preferred_ps_age"] = profile.preferred_ps_age

        # 6) preferred_methods
        try:
            selected = profile.preferred_methods.values_list("id", flat=True)
            initial["preferred_methods"] = list(selected)
        except Exception:
            initial["preferred_methods"] = []

        # 7) has_time_preferences
        initial["has_time_preferences"] = profile.has_time_preferences

        # 8) preferred_slots
        initial["preferred_slots"] = profile.preferred_slots

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
        return build_topics_grouped_by_type()

    def get_success_url(self):
        """Формирует URL следующего шага с сохранением текущего layout."""
        return f"{reverse('core:choice-psychologist')}{self._build_layout_query()}"

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в HTML-шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) Возвращает:
        - dict: словарь со всеми данными, доступными внутри HTML-шаблона."""
        context = super().get_context_data(**kwargs)

        form = context["form"]

        context["preferred_topic_type"] = form.initial.get("preferred_topic_type", "individual")
        # requested_topics: 1) группируем; 2) превращаем PK тем в строки, чтобы удобнее работать в JS
        context["topics_by_type"] = self._group_topics()
        context["selected_topics"] = [
            str(pk) for pk in form.initial.get("requested_topics", [])
        ]
        context["has_preferences"] = form.initial.get("has_preferences", False)
        context["preferred_ps_gender"] = form.initial.get("preferred_ps_gender", [])
        context["preferred_ps_age"] = form.initial.get("preferred_ps_age", [])
        # preferred_methods (для шаблона превращаем PK методов в строки, чтобы удобнее работать в JS)
        context["methods"] = Method.objects.all().order_by("name")
        context["selected_methods"] = [
            str(pk) for pk in form.initial.get("preferred_methods", [])
        ]
        context["has_time_preferences"] = form.initial.get("has_time_preferences", False)
        # preferred_slots (сразу сериализоруем потому что JS не должен работать с Python datetime)
        context["preferred_slots"] = [
            slot.isoformat()
            for slot in form.initial.get("preferred_slots", [])
        ]
        context["title_home_page_view"] = "Психологи онлайн на Опора — поиск и подбор психолога"

        # Логика управление отображением сайдбара:
        # 1) если пришли из сайдбара, показываем его;
        # 2) и показываем верхнее меню без сайдбара, если открыли не из сайдбара
        self._apply_layout_context(context)

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "psychologist-match"

        return context

    def form_valid(self, form):
        """Сохраняем изменения в профиле (fallback-сохранение, если AJAX не сработал)."""
        profile = get_object_or_404(ClientProfile, user=self.request.user)

        # 1) preferred_topic_type
        profile.preferred_topic_type = form.cleaned_data.get("preferred_topic_type")

        # 2) requested_topics
        selected_topics = form.cleaned_data["requested_topics"]
        profile.requested_topics.set(selected_topics)

        # 3) has_preferences
        profile.has_preferences = form.cleaned_data.get("has_preferences", False)

        # 4) preferred_ps_gender
        profile.preferred_ps_gender = form.cleaned_data.get("preferred_ps_gender") or []

        # 5) preferred_ps_age
        profile.preferred_ps_age = form.cleaned_data.get("preferred_ps_age") or []

        # 6) preferred_methods
        selected_methods = form.cleaned_data["preferred_methods"]
        profile.preferred_methods.set(selected_methods)

        # 7) has_time_preferences
        profile.has_time_preferences = form.cleaned_data.get("has_time_preferences", False)

        profile.save()

        # Маркер: что после новой фильтрации на странице выбора психолога нужно стартовать с АВЫ первого,
        # то есть нужно будет сбрасывать запоминание карточки последнего психолога, которое есть при просмотре
        # детальной инфо на след странице и выборе слота для записи
        self.request.session["reset_choice_psychologist"] = True

        return super().form_valid(form)
