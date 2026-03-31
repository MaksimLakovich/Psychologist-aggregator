from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator
from django.views.generic import FormView

from calendar_engine.booking.exceptions import CreateBookingValidationError
from calendar_engine.booking.services import build_specialist_live_indicator
from calendar_engine.lifecycle.exceptions import LifecycleActionValidationError
from calendar_engine.lifecycle.use_cases.cancel_event import cancel_event_slot
from calendar_engine.lifecycle.use_cases.reschedule_therapy_session import \
    reschedule_therapy_session_slot
from calendar_engine.models import TimeSlotMessage
from core.constants import (
    MESSAGE_EDIT_WINDOW_SECONDS_IN_THERAPY_SESSION_PAGE,
    MESSAGE_LENGTH_IN_THERAPY_SESSION_PAGE,
    VISIBLE_MESSAGE_LIMITS_IN_THERAPY_SESSION_PAGE)
from core.forms.client.my_account.form_therapy_session_details import (
    CancelTherapySessionForm, ClientTherapySessionDetailsForm,
    RescheduleTherapySessionForm)
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
    form_class = ClientTherapySessionDetailsForm
    # Количество сообщение которые отображаются по умолчанию в детальной карточке *Терапевтическая сессия*
    visible_messages_limit = VISIBLE_MESSAGE_LIMITS_IN_THERAPY_SESSION_PAGE
    # Количество символов в сообщении по умолчанию в детальной карточке *Терапевтическая сессия*
    message_length = MESSAGE_LENGTH_IN_THERAPY_SESSION_PAGE
    # В течение какого времени после публикации автор еще может РЕДАКТИРОВАТЬ текст своего сообщения
    message_edit_window_seconds = MESSAGE_EDIT_WINDOW_SECONDS_IN_THERAPY_SESSION_PAGE

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
        # load_therapy_session_detail_data(...) загружает общую detail-основу для терапевтической встречи
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
        context["can_manage_session_actions"] = self._can_manage_session_actions()
        context["cancel_session_form"] = CancelTherapySessionForm(
            initial={
                "action": "cancel_session",
                "cancel_reason_type": "cancelled_by_user",
            }
        )
        context["reschedule_session_form"] = RescheduleTherapySessionForm(
            initial={
                "action": "reschedule_session",
                "previous_event_id": self.event.id,
            }
        )
        context["session_consultation_type"] = (
            "couple" if self.event.event_type == "session_couple" else "individual"
        )
        context["specialist_schedule_url"] = (
            reverse(
                "calendar:api:get-psychologist-schedule",
                kwargs={"profile_id": specialist_profile.pk},
            )
            if specialist_profile
            else None
        )
        context["client_timezone_value"] = getattr(self.request.user, "timezone", "") or ""
        context["current_slot_start_iso"] = (
            self.detail_data.slot_display_data.get("display_start_iso")
            if self.slot else ""
        )
        context["visible_messages_limit"] = self.visible_messages_limit
        context["remaining_comments_count"] = max(len(message_items) - self.visible_messages_limit, 0)
        context["specialist_live_indicator"] = build_specialist_live_indicator(
            specialist_profile=specialist_profile,
        )

        return context

    def post(self, request, *args, **kwargs):
        """Маршрутизирует POST-действия detail-страницы:
            - cancel/reschedule встречи обрабатываются отдельными lifecycle-методами;
            - остальные POST-запросы относятся к forum-форме: стандартная FormView через super().post(...).
        """
        action = request.POST.get("action")

        if action == "cancel_session":
            return self._handle_cancel_session()

        if action == "reschedule_session":
            return self._handle_reschedule_session()

        return super().post(request, *args, **kwargs)

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

    def form_invalid(self, form):
        """Разводит обработку ошибок для добавления и inline-редактирования сообщения.

        Бизнес-смысл:
            - нижняя форма страницы отвечает за добавление нового сообщения;
            - inline-форма внутри карточки сообщения отвечает за редактирование уже существующего;
            - если edit-message не прошел проверку, нельзя оставлять page-form в связанном состоянии
              action=edit_message, иначе следующий submit кнопки "Добавить сообщение" повторит старую ошибку.
        """
        if self.request.POST.get("action") == "edit_message":
            error_text = next(iter(form.non_field_errors()), None)
            if error_text is None:
                error_text = next(iter(form.errors.get("message", [])), "Не удалось обновить сообщение!")

            messages.error(self.request, error_text)
            return redirect(self.get_success_url())

        return super().form_invalid(form)

    def get_success_url(self):
        """После сохранения остаемся на той же detail-странице и сохраняем текущий layout."""
        return f"{self.request.path}{self._build_layout_query()}"

    def _get_event_detail_url(self, *, event_id):
        """Возвращает URL детальной страницы для указанного события после таких действий, как редактирование или
        перенос события, чтоб оставаться внутри обновленного события."""
        return (
            f"{reverse('core:client-therapy-session-detail', kwargs={'event_id': event_id})}"
            f"{self._build_layout_query()}"
        )

    def _can_manage_session_actions(self):
        """Определяет, доступны ли клиенту cancel/reschedule для текущего слота (события)."""
        return bool(
            self.slot
            and self.slot.status in ["planned", "started"]
            and not self.detail_data.is_finished_slot
        )

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

    def _handle_action_form_error(self, form):
        """Показывает понятную flash-ошибку и возвращает пользователя обратно на detail-экран при работе
        с функционалом cancel/reschedule."""
        # Сначала пробуем показать пользователю самую важную общую ошибку, т.е.:
        # 1) Сначала пробуем взять общую ошибку формы через form.non_field_errors()
        error_text = next(iter(form.non_field_errors()), None)

        # 2) Если общей ошибки нет, берем первое поле с ошибкой и достаем текст этой ошибки через form.errors.keys()
        if error_text is None:
            first_field_name = next(iter(form.errors.keys()), None)
            error_values = form.errors.get(first_field_name, []) if first_field_name else []
            # 3) Если и у поля не удалось получить текст, показываем запасное сообщение
            error_text = next(iter(error_values), "Не удалось выполнить действие со встречей.")

        messages.error(self.request, error_text)

        return redirect(self.get_success_url())

    def _handle_cancel_session(self):
        """Отменяет текущую встречу по инициативе клиента."""
        form = CancelTherapySessionForm(self.request.POST)

        # 1) Определяем доступен ли клиенту cancel для текущего слота (события)
        if not self._can_manage_session_actions():
            messages.error(self.request, "Отменить можно только встречу, которая еще не завершена.")
            return redirect(self.get_success_url())

        # 2) Показываем понятную flash-ошибку
        if not form.is_valid():
            return self._handle_action_form_error(form)

        # 3) Выполняем "ОТМЕНУ"
        try:
            cancel_event_slot(
                slot=self.slot,
                cancel_reason=form.cleaned_data["cancel_reason"],
            )
        # Это уже проверка бизнес-логики и текущего состояния встречи внутри use case. Т.е., форма может быть
        # заполнена идеально, но действие все равно нельзя выполнить:
        # - пока пользователь держал модалку открытой, встреча уже завершилась
        # - слот уже кто-то успел отменить
        # - слот уже нельзя менять по lifecycle-правилам
        except LifecycleActionValidationError as exc:
            messages.error(self.request, str(exc))
            return redirect(self.get_success_url())

        messages.success(self.request, "Встреча отменена!")

        return redirect(self.get_success_url())

    def _handle_reschedule_session(self):
        """Создает новую встречу на другое время и помечает текущую как перенесенную."""
        form = RescheduleTherapySessionForm(self.request.POST)

        # 1) Определяем доступен ли клиенту reschedule для текущего слота (события)
        if not self._can_manage_session_actions():
            messages.error(self.request, "Перенести можно только встречу, которая еще не завершена.")
            return redirect(self.get_success_url())

        # 2) Показываем понятную flash-ошибку
        if not form.is_valid():
            return self._handle_action_form_error(form)

        # 3) Проверяем что фиксация обязательного параметра previous_event_id доступна
        if str(form.cleaned_data["previous_event_id"]) != str(self.event.id):
            messages.error(self.request, "Не удалось корректно определить исходную встречу для переноса.")
            return redirect(self.get_success_url())

        # 4) Подтягиваем данные специалиста
        specialist_profile = self._get_specialist_profile()
        if specialist_profile is None:
            messages.error(self.request, "Не удалось определить специалиста для переноса встречи.")
            return redirect(self.get_success_url())

        # 5) Фиксируем тот же тип сессии, что и был
        consultation_type = "couple" if self.event.event_type == "session_couple" else "individual"

        # 6) Выполняем "ПЕРЕНОС"
        try:
            booking_result = reschedule_therapy_session_slot(
                slot=self.slot,
                client_user=self.request.user,
                specialist_profile_id=specialist_profile.pk,
                slot_start_iso=form.cleaned_data["slot_start_iso"],
                consultation_type=consultation_type,
                cancel_reason=form.cleaned_data["cancel_reason"],
            )
        # Это уже проверка бизнес-логики и текущего состояния встречи внутри use case. Т.е., форма может быть
        # заполнена идеально, но действие все равно нельзя выполнить:
        # - пока пользователь держал модалку открытой, встреча уже завершилась
        # - слот уже кто-то успел отменить
        # - слот уже нельзя менять по lifecycle-правилам
        except (LifecycleActionValidationError, CreateBookingValidationError) as exc:
            messages.error(self.request, str(exc))
            return redirect(self.get_success_url())

        messages.success(self.request, "Встреча перенесена!")

        return redirect(self._get_event_detail_url(event_id=booking_result["event"].id))

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

    def _create_slot_message(self, form):
        """Создает новое сообщение текущего пользователя внутри активной встречи."""
        slot_message = TimeSlotMessage(
            creator=self.request.user,
            slot=self.slot,
            message=form.cleaned_data["message"],
        )
        slot_message.full_clean()
        slot_message.save()

    def _can_edit_slot_message(self, slot_message):
        """Проверяет, доступно ли автору редактирование конкретного сообщения.

        Бизнес-смысл:
            - одного условия "встреча еще активна" недостаточно:
              иначе сообщение можно переписывать сколько угодно долго до конца встречи;
            - поэтому вводим дополнительное окно редактирования после created_at;
            - итоговое правило:
                - сообщение принадлежит текущему пользователю;
                - встреча еще допускает работу с форумом;
                - с момента публикации прошло не больше заданного лимита секунд.
        """
        if slot_message.creator_id != self.request.user.pk:
            return False

        if not self._can_manage_slot_messages():
            return False

        editable_until = slot_message.created_at + timedelta(seconds=self.message_edit_window_seconds)
        return timezone.now() <= editable_until

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
        if not self._can_edit_slot_message(slot_message):
            form.add_error(
                None,
                f"Редактировать сообщение можно только в течение первых "
                f"{self.message_edit_window_seconds // 60} минут после публикации.",
            )
            return self.form_invalid(form)

        new_message = form.cleaned_data["message"]

        if slot_message.message != new_message:
            slot_message.message = new_message
            slot_message.is_rewrited = True
            slot_message.full_clean()
            slot_message.save(update_fields=["message", "is_rewrited", "updated_at"])

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
                    "can_edit": self._can_edit_slot_message(slot_message),
                    "creator_full_name": creator_full_name or slot_message.creator.email,
                    "creator_avatar_url": slot_message.creator.avatar_url,
                    "created_at_display": local_created_at.strftime("%d.%m.%Y %H:%M"),
                    "updated_at_display": local_updated_at.strftime("%d.%m.%Y %H:%M"),
                }
            )

        return message_items
