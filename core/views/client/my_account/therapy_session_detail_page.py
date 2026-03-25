from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from core.forms.client.my_account.form_therapy_session_details import ClientTherapySessionDetailsForm
from core.services.experience_label import build_experience_label
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin
from core.services.therapy_session.therapy_session_detail_loader import load_therapy_session_detail_data
from users.constants import LANGUAGE_CHOICES


class ClientTherapySessionDetailView(SpecialistMatchingLayoutMixin, LoginRequiredMixin, FormView):
    """Детальная страница одной терапевтической сессии клиента."""

    template_name = "core/client_pages/my_account/therapy_session_detail.html"
    form_class = ClientTherapySessionDetailsForm

    def dispatch(self, request, *args, **kwargs):
        """Подготавливает всю detail-страницу еще до перехода в GET/POST-логику.

        Бизнес-смысл:
            - клиент открывает страницу конкретной терапевтической сессии по event_id;
            - система должна сразу убедиться, что этот клиент действительно участвует в данной встрече
              и не пытается открыть чужое событие по прямой ссылке;
            - после этого shared loader один раз загружает общую основу detail-screen:
                - событие;
                - display-slot;
                - второго участника;
                - display-дату и время;
                - базовые счетчики и флаги страницы.

        Суть:
            - dispatch() вызывается раньше get_initial(), form_valid() и get_context_data();
            - значит остальные методы класса могут работать уже с готовыми self.detail_data,
              self.event и self.slot без повторной загрузки одной и той же встречи из БД.
        """
        self.detail_data = load_therapy_session_detail_data(
            viewer_user=request.user,
            event_id=kwargs["event_id"],
            viewer_timezone=getattr(request.user, "timezone", None),
        )
        self.event = self.detail_data.event
        self.slot = self.detail_data.slot

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Предзаполняем форму текущими значениями из актуального слота сессии в БД."""
        initial = super().get_initial()
        if self.slot is None:
            return initial

        initial.update(
            {
                "comment": self.slot.comment or "",
            }
        )

        return initial

    def form_valid(self, form):
        """Сохраняет редактируемые поля актуального слота текущей терапевтической сессии."""
        if self.slot is None:
            form.add_error(None, "У сессии не найден актуальный слот. Сохранение невозможно.")

            return self.form_invalid(form)

        # Обновляем только те поля, которые на текущем этапе согласованы как безопасно редактируемые:
        # - на клиентской странице сохраняем только комментарий;
        # - meeting_url готовит специалист, поэтому клиент не должен менять ссылку на созвон
        self.slot.comment = form.cleaned_data["comment"]
        self.slot.full_clean()  # Дополнительная защитная модельная валидация перед записью в БД
        self.slot.save(update_fields=["comment", "updated_at"])

        messages.success(self.request, "Детали сессии успешно обновлены!")

        return redirect(self.get_success_url())

    def get_success_url(self):
        """После сохранения остаемся на той же detail-странице и сохраняем текущий layout."""
        return f"{self.request.path}{self._build_layout_query()}"

    def _get_specialist_profile(self):
        """Возвращает профиль специалиста из shared detail loader для клиентской страницы.

        Бизнес-смысл:
            - текущая страница всегда открывается клиентом;
            - shared loader уже нашел counterpart_user;
            - в клиентском сценарии counterpart = это специалист;
            - поэтому здесь просто безопасно достаем psychologist_profile без повторного поиска участника.
        """
        counterpart_user = self.detail_data.counterpart_user

        if counterpart_user is None:
            return None

        return getattr(counterpart_user, "psychologist_profile", None)

    def _build_matched_topics(self):
        """Собирает все совпадающие темы между анкетой клиента и темами специалиста для detail-screen сессии.

        Бизнес-смысл:
            - страница детали уже не участвует в процессе подбора специалиста;
            - здесь клиенту важно увидеть полную картину пересечений по своей анкете,
              а не только темы одного выбранного ранее типа консультации;
            - поэтому на detail-screen показываем все совпадения:
                - индивидуальные;
                - парные.
        """
        try:
            client_profile = self.request.user.client_profile
        except Exception:
            return []

        specialist_profile = self._get_specialist_profile()
        if specialist_profile is None:
            return []

        # На detail-странице берем все темы клиента из анкеты без ограничения по preferred_topic_type:
        # эта страница уже не подбирает специалиста по одному сценарию, а показывает итоговое
        # пересечение анкеты клиента с рабочими темами конкретного специалиста
        requested_topic_ids = client_profile.requested_topics.values_list("id", flat=True)

        return list(
            specialist_profile.topics.filter(
                id__in=requested_topic_ids,
            ).order_by("group_name", "name")
        )

    def get_context_data(self, **kwargs):
        """Формирует контекст detail-screen терапевтической сессии."""
        context = super().get_context_data(**kwargs)
        language_label_map = dict(LANGUAGE_CHOICES)
        specialist_profile = self._get_specialist_profile()
        counterpart_user = self.detail_data.counterpart_user

        specialist_languages_display = (
            [
                language_label_map.get(language_code, language_code)
                for language_code in specialist_profile.languages
            ]
            if specialist_profile and specialist_profile.languages
            else []
        )
        experience_label = build_experience_label(
            specialist_profile.work_experience_years if specialist_profile else None
        )

        if specialist_profile and self.event.event_type == "session_couple":
            session_price_value = specialist_profile.price_couples
        else:
            session_price_value = specialist_profile.price_individual if specialist_profile else None

        context["title_client_account_view"] = "Детали сессии на ОПОРА"
        self._apply_layout_context(context)
        context["current_sidebar_key"] = "all-events"
        context["event"] = self.event
        context["slot"] = self.slot
        context["counterpart_full_name"] = (
            self.detail_data.counterpart_full_name or "Специалист будет указан позже"
        )
        context["specialist_profile"] = specialist_profile
        context["specialist_photo_url"] = (
            counterpart_user.avatar_url
            if counterpart_user
            else "/static/images/menu/user-circle.svg"
        )
        context["specialist_profile_url"] = (
            f"{reverse('core:psychologist-card-detail', kwargs={'profile_slug': specialist_profile.slug})}"
            f"{self._build_layout_query()}"
            if specialist_profile and specialist_profile.slug
            else None
        )
        context["specialist_experience_label"] = experience_label
        context["specialist_languages_display"] = specialist_languages_display
        context["session_price_value"] = session_price_value
        # Время и дата уже заранее подготовлены shared loader по timezone текущего пользователя.
        context["slot_display"] = self.detail_data.slot_display_data
        # Видеочат для клиента имеет смысл только пока встреча еще активна.
        # Если слот уже завершился по статусу или по времени, кнопку перехода в звонок скрываем
        context["can_open_meeting_url"] = self.detail_data.can_open_meeting_url
        context["slot_participants_count"] = self.detail_data.slot_participants_count
        context["event_participants_count"] = self.detail_data.event_participants_count
        context["matched_topics"] = self._build_matched_topics()

        return context
