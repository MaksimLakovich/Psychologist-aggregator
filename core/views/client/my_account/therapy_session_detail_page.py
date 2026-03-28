from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator
from django.views.generic import FormView

from calendar_engine.booking.services import build_specialist_live_indicator
from calendar_engine.models import TimeSlotMessage
from core.constants import VISIBLE_MESSAGE_LIMITS_IN_THERAPY_SESSION_PAGE, MESSAGE_LENGTH_IN_THERAPY_SESSION_PAGE
from core.forms.forum_message.form_forum_message import ForumMessageForm
from core.services.experience_label import build_experience_label
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin
from core.services.therapy_session.therapy_session_detail_loader import \
    load_therapy_session_detail_data
from users.constants import LANGUAGE_CHOICES


class ClientTherapySessionDetailView(SpecialistMatchingLayoutMixin, LoginRequiredMixin, FormView):
    """Детальная страница одной терапевтической сессии клиента."""

    template_name = "core/client_pages/my_account/therapy_session_detail.html"
    # Форумная часть встречи теперь живет в нейтральной shared-форме,
    # потому что этот же input-contract позже понадобится и специалисту, и другим типам событий
    form_class = ForumMessageForm
    # Количество сообщение которые отображаются по умолчанию в детальной карточке *Терапевтическая сессия*
    visible_messages_limit = VISIBLE_MESSAGE_LIMITS_IN_THERAPY_SESSION_PAGE
    # Количество символов в сообщении по умолчанию в детальной карточке *Терапевтическая сессия*
    message_length = MESSAGE_LENGTH_IN_THERAPY_SESSION_PAGE

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
        """1) Предзаполняем форму текущими значениями из актуального слота сессии в БД.
        2) По умолчанию открывает forum-форму в режиме добавления нового сообщения."""
        initial = super().get_initial()
        initial.update(
            {
                "action": "add_message",
            }
        )

        return initial

    def form_valid(self, form):
        """Обрабатывает forum-действия внутри активной встречи."""
        if self.slot is None:
            form.add_error(None, "У сессии не найден актуальный слот. Отправка сообщения невозможна.")
            return self.form_invalid(form)

        if not self._can_manage_slot_messages():  # Определяет, можно ли сейчас писать/редактировать сообщение
            form.add_error(None, "Оставлять и редактировать сообщения можно только в активной встрече.")
            return self.form_invalid(form)

        # Создание / Редактирование сообщения текущего пользователя внутри активной встречи
        if form.cleaned_data["action"] == "edit_message":
            edit_result = self._edit_slot_message(form)
            if edit_result is not None:
                return edit_result
            messages.success(self.request, "Сообщение обновлено!")
        else:
            self._create_slot_message(form)
            messages.success(self.request, "Сообщение добавлено!")

        return redirect(self.get_success_url())

    def get_success_url(self):
        """После сохранения остаемся на той же detail-странице и сохраняем текущий layout."""
        return f"{self.request.path}{self._build_layout_query()}"

    def _can_manage_slot_messages(self):
        """Определяет, можно ли сейчас писать и редактировать сообщения внутри встречи.

        Бизнес-смысл:
            - форум внутри страницы детали должен быть активен только пока сама встреча еще активна;
            - после завершения слота история сообщений остается доступной для чтения,
              но новые сообщения и редактирование блокируются.
        """
        return bool(
            self.slot
            and self.slot.status in ["planned", "started"]
            and not self.detail_data.is_finished_slot
        )

    def _create_slot_message(self, form):
        """Создает новое сообщение текущего пользователя внутри активной встречи."""
        slot_message = TimeSlotMessage(
            creator=self.request.user,
            slot=self.slot,
            message=form.cleaned_data["message"],
        )
        slot_message.full_clean()
        slot_message.save()

    def _edit_slot_message(self, form):
        """Редактирует сообщение текущего пользователя внутри активной встречи.

        Бизнес-смысл:
            - редактировать можно только свое сообщение;
            - после изменения текста ставим флаг is_rewrited, чтобы UI показывал пометку "отредактировано".
        """
        message_id = form.cleaned_data.get("message_id")
        if message_id is None:
            form.add_error(None, "Не найдено сообщение для редактирования.")
            return self.form_invalid(form)

        slot_message = get_object_or_404(
            TimeSlotMessage,
            pk=message_id,
            slot=self.slot,
            creator=self.request.user,
        )
        new_message = form.cleaned_data["message"]

        if slot_message.message != new_message:
            slot_message.message = new_message
            slot_message.is_rewrited = True
            slot_message.full_clean()
            slot_message.save(update_fields=["message", "is_rewrited", "updated_at"])

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

    def _build_message_items(self):
        """Готовит display-контракт сообщений для forum-блока страницы.

        Бизнес-смысл:
            - шаблону нужны не сырые ORM-объекты, а уже готовые значения для UX:
                - направление сообщения (слева/справа);
                - можно ли редактировать;
                - нужно ли показывать кнопку "показать все";
                - локальное время сообщения для текущего пользователя.
        """
        if self.slot is None:
            return []

        client_timezone = getattr(self.request.user, "timezone", None)
        message_items = []

        for slot_message in self.slot.messages.all():
            local_created_at = timezone.localtime(slot_message.created_at, client_timezone)
            local_updated_at = timezone.localtime(slot_message.updated_at, client_timezone)
            creator_full_name = f"{slot_message.creator.first_name} {slot_message.creator.last_name}".strip()
            is_own_message = slot_message.creator_id == self.request.user.pk

            message_items.append(
                {
                    "id": str(slot_message.pk),
                    "comment": slot_message,
                    "message_preview": Truncator(slot_message.message).chars(self.message_length, truncate="..."),
                    "is_long_message": len(slot_message.message) > self.message_length,
                    "is_own_message": is_own_message,
                    "can_edit": is_own_message and self._can_manage_slot_messages(),
                    "creator_full_name": creator_full_name or slot_message.creator.email,
                    "creator_avatar_url": slot_message.creator.avatar_url,
                    "created_at_display": local_created_at.strftime("%d.%m.%Y %H:%M"),
                    "updated_at_display": local_updated_at.strftime("%d.%m.%Y %H:%M"),
                }
            )

        return message_items

    def get_context_data(self, **kwargs):
        """Формирует контекст detail-страницу терапевтической сессии."""
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
        # Время и дата уже заранее подготовлены shared loader по timezone текущего пользователя
        context["slot_display"] = self.detail_data.slot_display_data
        # Отдельный флаг нужен шаблону, чтобы в архивной встрече вместо подключения показывать meeting_resume
        # + для slate-стиля в блоке общая инфо по встрече
        context["is_finished_slot"] = self.detail_data.is_finished_slot
        # Видеочат для клиента имеет смысл только пока встреча еще активна.
        # Если слот уже завершился по статусу или по времени, кнопку перехода в звонок скрываем
        context["can_open_meeting_url"] = self.detail_data.can_open_meeting_url
        context["slot_participants_count"] = self.detail_data.slot_participants_count
        context["event_participants_count"] = self.detail_data.event_participants_count
        context["matched_topics"] = self._build_matched_topics()
        message_items = self._build_message_items()
        context["message_items"] = message_items
        context["can_manage_slot_messages"] = self._can_manage_slot_messages()
        context["visible_messages_limit"] = self.visible_messages_limit
        context["remaining_comments_count"] = max(len(message_items) - self.visible_messages_limit, 0)
        context["specialist_live_indicator"] = build_specialist_live_indicator(
            specialist_profile=specialist_profile,
        )

        return context
