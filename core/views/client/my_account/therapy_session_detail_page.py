from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView

from calendar_engine.models import CalendarEvent
from core.forms.client.my_account.form_therapy_session_details import \
    ClientTherapySessionDetailsForm
from core.services.calendar_event_slot_selector import (
    get_event_active_slot,
    get_event_completed_slot,
)
from core.services.calendar_slot_time_display import \
    build_calendar_slot_time_display
from core.services.experience_label import build_experience_label
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin
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
            - после этого один раз загружаем само событие и только те связанные данные,
              которые действительно нужны дальше для всей страницы:
                - слот сессии;
                - участники;
                - профиль специалиста;
                - темы специалиста для блока matched topics.

        Суть:
            - dispatch() вызывается раньше get_initial(), form_valid() и get_context_data();
            - значит остальные методы класса могут работать уже с готовыми self.event и self.slot,
              без повторных поисков одного и того же события в БД.
        """
        self.event = get_object_or_404(
            CalendarEvent.objects.prefetch_related(
                "slots",
                "slots__slot_participants__user",
                "participants__user__psychologist_profile",
                "participants__user__psychologist_profile__methods",
                "participants__user__psychologist_profile__specialisations",
                "participants__user__psychologist_profile__topics",
            ),
            id=kwargs["event_id"],
            participants__user=request.user,
        )
        # Для detail-screen сначала пробуем взять активный слот:
        #   - это основной сценарий для будущих и текущих встреч.
        # Если active-slot не найден, значит клиент, скорее всего, открыл уже завершенное событие из архива.
        # Тогда переключаемся на completed-slot, чтобы страница деталей корректно работала и для прошлых встреч.
        self.slot = get_event_active_slot(self.event) or get_event_completed_slot(self.event)
        if self.slot is None:
            fallback_completed_slots = [
                event_slot
                for event_slot in self.event.slots.all()
                if event_slot.end_datetime < timezone.now()
            ]
            self.slot = next(iter(reversed(fallback_completed_slots)), None)

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Предзаполняем форму текущими значениями из актуального слота сессии в БД."""
        initial = super().get_initial()
        if self.slot is None:
            return initial

        initial.update(
            {
                "meeting_url": self.slot.meeting_url or "",
                "comment": self.slot.comment or "",
            }
        )

        return initial

    def form_valid(self, form):
        """Сохраняет редактируемые поля актуального слота текущей терапевтической сессии."""
        if self.slot is None:
            form.add_error(None, "У сессии не найден актуальный слот. Сохранение невозможно.")

            return self.form_invalid(form)

        # Обновляем только те поля, которые на текущем этапе согласованы как безопасно редактируемые
        self.slot.meeting_url = form.cleaned_data["meeting_url"]
        self.slot.comment = form.cleaned_data["comment"]
        self.slot.full_clean()  # Дополнительная защитная модельная валидация перед записью в БД
        self.slot.save(update_fields=["meeting_url", "comment", "updated_at"])

        messages.success(self.request, "Детали сессии успешно обновлены!")

        return redirect(self.get_success_url())

    def get_success_url(self):
        """После сохранения остаемся на той же detail-странице и сохраняем текущий layout."""
        return f"{self.request.path}{self._build_layout_query()}"

    def _get_counterpart_user_and_specialist_profile(self):
        """Возвращает данные второй стороны терапевтической сессии для detail-screen.

        Бизнес-смысл:
            - текущая страница всегда открывается клиентом;
            - значит второй участник события для нас - это специалист;
            - эти данные нужны сразу в нескольких местах:
                - для шапки страницы с именем и фото специалиста;
                - для блока matched topics;
                - для будущих расширений detail-screen, где могут понадобиться и другие поля специалиста.

        Возвращаем:
            - counterpart_participant: связь участника с событием;
            - counterpart_user: пользователь-специалист;
            - specialist_profile: профиль специалиста.
        """
        counterpart_participant = next(
            (
                participant
                for participant in self.event.participants.all()
                if participant.user_id != self.request.user.pk
            ),
            None,
        )
        counterpart_user = counterpart_participant.user if counterpart_participant else None
        specialist_profile = (
            getattr(counterpart_user, "psychologist_profile", None)
            if counterpart_user
            else None
        )

        return counterpart_participant, counterpart_user, specialist_profile

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

        _, _, specialist_profile = self._get_counterpart_user_and_specialist_profile()
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
        client_timezone = getattr(self.request.user, "timezone", None)
        language_label_map = dict(LANGUAGE_CHOICES)

        _, counterpart_user, specialist_profile = self._get_counterpart_user_and_specialist_profile()
        counterpart_full_name = (
            f"{counterpart_user.first_name} {counterpart_user.last_name}".strip()
            if counterpart_user
            else ""
        )
        # Дату и время detail-screen рассчитываем по той же display-логике, что и на странице списка:
        # клиент всегда должен видеть сессию в своем текущем timezone, даже если позже поменял его в профиле.
        slot_display_data = (
            build_calendar_slot_time_display(
                slot=self.slot,
                client_timezone=client_timezone,
            )
            if self.slot
            else {}
        )
        specialist_languages_display = (
            [language_label_map.get(language_code, language_code) for language_code in specialist_profile.languages]
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
        context["counterpart_full_name"] = counterpart_full_name or "Специалист будет указан позже"
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
        context["slot_display"] = slot_display_data
        # Видеочат для клиента имеет смысл только пока встреча еще активна.
        # Если слот уже завершился по статусу или по времени, кнопку перехода в звонок скрываем
        context["can_open_meeting_url"] = bool(
            self.slot
            and self.slot.meeting_url
            and self.slot.status != "completed"
            and self.slot.end_datetime >= timezone.now()
        )
        context["slot_participants_count"] = len(self.slot.slot_participants.all()) if self.slot else 0
        context["event_participants_count"] = len(self.event.participants.all())
        context["matched_topics"] = self._build_matched_topics()

        return context
