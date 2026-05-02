from datetime import timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator
from django.views.generic import FormView

from calendar_engine.booking.exceptions import CreateBookingValidationError
from calendar_engine.lifecycle.exceptions import LifecycleActionValidationError
from calendar_engine.lifecycle.services.reschedule_chain_resolver import \
    get_latest_rescheduled_descendant
from calendar_engine.lifecycle.services.slot_status_display import \
    build_calendar_slot_status_display
from calendar_engine.lifecycle.use_cases.cancel_event import cancel_event_slot
from calendar_engine.lifecycle.use_cases.reschedule_therapy_session import \
    reschedule_therapy_session_slot
from calendar_engine.models import TimeSlotMessage
from core.constants import (
    MESSAGE_EDIT_WINDOW_SECONDS_IN_THERAPY_SESSION_PAGE,
    MESSAGE_LENGTH_IN_THERAPY_SESSION_PAGE,
    VISIBLE_MESSAGE_LIMITS_IN_THERAPY_SESSION_PAGE)
from core.forms.client.my_account.form_therapy_session_details import (
    CancelTherapySessionForm, RescheduleTherapySessionForm)
from core.forms.psychologist.my_account.form_therapy_session_details import \
    PsychologistTherapySessionDetailsForm
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin
from core.services.therapy_session.therapy_session_detail_loader import \
    load_therapy_session_detail_data
from users.mixins.role_required_mixin import PsychologistRequiredMixin


class PsychologistTherapySessionDetailView(PsychologistRequiredMixin, SpecialistMatchingLayoutMixin, FormView):
    """Детальная страница терапевтической сессии со стороны специалиста.

    Бизнес-смысл:
        - специалист открывает встречу из своего календаря и видит клиента, дату, время и статус;
        - специалист управляет организационными данными встречи:
            - ссылкой на подключение;
            - описанием события;
            - итогами после начала/завершения встречи;
        - специалист, как и клиент, может отменять/переносить активную встречу;
        - forum-блок общий для обеих сторон, чтобы клиент и специалист могли обмениваться сообщениями
          внутри одной терапевтической сессии.
    """

    template_name = "core/psychologist_pages/my_account/therapy_session_detail.html"
    # Форумная часть встречи теперь живет в нейтральной shared-форме,
    # потому что этот же input-contract позже понадобится и специалисту, и другим типам событий
    form_class = PsychologistTherapySessionDetailsForm
    # Количество сообщение которые отображаются по умолчанию в детальной карточке *Терапевтическая сессия*
    visible_messages_limit = VISIBLE_MESSAGE_LIMITS_IN_THERAPY_SESSION_PAGE
    # Количество символов в сообщении по умолчанию в детальной карточке *Терапевтическая сессия*
    message_length = MESSAGE_LENGTH_IN_THERAPY_SESSION_PAGE
    # В течение какого времени после публикации автор еще может РЕДАКТИРОВАТЬ текст своего сообщения
    message_edit_window_seconds = MESSAGE_EDIT_WINDOW_SECONDS_IN_THERAPY_SESSION_PAGE

    def dispatch(self, request, *args, **kwargs):
        """Подготавливает всю detail-страницу еще до перехода в GET/POST-логику.

        Бизнес-смысл:
            - пользователь открывает страницу конкретной терапевтической сессии по event_id;
            - система должна сразу убедиться, что этот пользователь действительно участвует в данной встрече
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
        # ВАЖНО:
        # check_role_access(...) вызываем здесь вручную ДО загрузки detail_data из БД.
        # Это нужно:
        # 1) Эта view теперь наследуется от PsychologistRequiredMixin.
        # 2) Но в этой конкретной странице мы сами переопределили dispatch(), а значит сначала выполняется
        #    код этого метода, и только потом super().dispatch(...).
        # 3) Если не сделать раннюю проверку роли здесь, то любая роль кроме psychologist сначала успеет зайти в
        #    load_therapy_session_detail_data(...), и только потом сработает общий dispatch mixin'а.
        # 4) Нам это не подходит: для чужой роли нужно остановиться как можно раньше и вообще не начинать
        #    загрузку специфических данных detail-экрана.
        # Итого:
        #   - если доступ разрешен, check_role_access(...) вернет None и мы продолжим;
        #   - если доступ запрещен, метод вернет готовый HttpResponse (redirect / 403), который сразу возвращаем
        access_response = self.check_role_access(request)
        if access_response is not None:
            return access_response

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
        """Метод:
        1) Предзаполняет форму текущими и организационными полями текущими значениями встречи из БД.
        2) По умолчанию открывает forum-форму в режиме добавления нового сообщения.
        """
        initial = super().get_initial()
        initial.update(
            {
                "action": "add_message",
                "meeting_url": self.slot.meeting_url if self.slot else "",
                "meeting_resume": self.slot.meeting_resume if self.slot else "",
                "event_description": self.event.description or "",
            }
        )
        return initial

    def get_context_data(self, **kwargs):
        """Формирует контекст detail-страницу терапевтической сессии."""
        context = super().get_context_data(**kwargs)
        self._apply_layout_context(context)

        specialist_profile = self._get_specialist_profile()
        if specialist_profile and self.event.event_type == "session_couple":
            session_price_value = specialist_profile.price_couples
        else:
            session_price_value = specialist_profile.price_individual if specialist_profile else None

        message_items = self._build_message_items()
        context["title_psychologist_account_view"] = "Детали сессии на ОПОРА"
        context["current_sidebar_key"] = "all-events"
        context["event"] = self.event
        context["slot"] = self.slot
        context["slot_status_display"] = build_calendar_slot_status_display(slot=self.slot)
        # Время и дата уже заранее подготовлены shared loader по timezone текущего пользователя
        context["slot_display"] = self.detail_data.slot_display_data
        # Отдельный флаг нужен шаблону, чтобы в архивной встрече вместо подключения показывать meeting_resume
        # + для slate-стиля в блоке общая инфо по встрече
        context["is_finished_slot"] = self.detail_data.is_finished_slot
        # Видеочат для клиента имеет смысл только пока встреча еще активна.
        # Если слот уже завершился по статусу или по времени, кнопку перехода в звонок скрываем
        context["can_open_meeting_url"] = self.detail_data.can_open_meeting_url
        context["detail_title_display"] = "Терапевтическая сессия с клиентом"
        context["counterpart_full_name"] = (
            self.detail_data.counterpart_full_name or "Имя клиента не указано"
        )
        context["client_user"] = self.detail_data.counterpart_user
        context["specialist_profile"] = specialist_profile
        context["session_price_value"] = session_price_value
        context["matched_topics"] = self._build_matched_topics()
        context["can_manage_meeting_url"] = self._can_manage_meeting_url()
        # Описание события показывается всем участникам в общем overview-блоке.
        # Но редактировать этот текст может только специалист прямо из этого же блока
        context["can_manage_event_description"] = True
        context["can_show_meeting_resume_block"] = self._can_show_meeting_resume_block()
        context["can_manage_meeting_resume"] = self._can_manage_meeting_resume()
        context["can_manage_slot_messages"] = self._can_manage_slot_messages()
        context["message_items"] = message_items
        context["visible_messages_limit"] = self.visible_messages_limit
        context["remaining_comments_count"] = max(len(message_items) - self.visible_messages_limit, 0)
        context["can_manage_session_actions"] = self._can_manage_session_actions()
        context["session_change_reason_label"] = self._get_session_change_reason_label()
        context["rescheduled_event_url"] = self._get_rescheduled_event_url()
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
        context["client_timezone_value"] = getattr(self.detail_data.counterpart_user, "timezone", "") or ""
        context["current_slot_start_iso"] = (
            self.detail_data.slot_display_data.get("display_start_iso")
            if self.slot else ""
        )

        return context

    def post(self, request, *args, **kwargs):
        """Маршрутизирует POST-действия специалиста на detail-странице:
            - cancel/reschedule встречи обрабатываются отдельными lifecycle-методами;
            - работа с meeting_url для видеовстречи;
            - работа с meeting_resume для фиксации итогов встречи;
            - работа с event_description для добавления доп описания ко встрече;
            - остальные POST-запросы относятся к forum-форме: стандартная FormView через super().post(...).
        """
        action = request.POST.get("action")

        if action == "cancel_session":
            return self._handle_cancel_session()
        if action == "reschedule_session":
            return self._handle_reschedule_session()
        if action == "save_meeting_url":
            return self._handle_save_meeting_url()
        if action == "delete_meeting_url":
            return self._handle_delete_meeting_url()
        if action == "save_meeting_resume":
            return self._handle_save_meeting_resume()
        if action == "save_event_description":
            return self._handle_save_event_description()

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        """Обрабатывает forum-действия внутри активной встречи."""
        if self.slot is None:
            form.add_error(None, "У сессии не найден актуальный слот. Отправка сообщения невозможна.")
            return self.form_invalid(form)

        if not self._can_manage_slot_messages():
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
            f"{reverse('core:psychologist-therapy-session-detail', kwargs={'event_id': event_id})}"
            f"{self._build_layout_query()}"
        )

    def _can_manage_session_actions(self):
        """Определяет, доступны ли пользователю cancel/reschedule для текущего слота (события)."""
        return bool(
            self.slot
            and self.slot.status in ["planned", "started"]
            and not self.detail_data.is_finished_slot
        )

    def _can_manage_slot_messages(self):
        """Определяет, можно ли сейчас писать/редактировать сообщения внутри встречи.

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

    def _can_manage_meeting_url(self):
        """Определяет, может ли специалист сейчас добавлять/редактировать ссылку на видеовстречу."""
        return bool(
            self.slot
            and self.slot.status in ["planned", "started"]
            and not self.detail_data.is_finished_slot
        )

    def _can_show_meeting_resume_block(self):
        """Показывает блок итогов после начала встречи и в архиве."""
        return bool(
            self.slot
            and self.slot.status in ["started", "completed"]
        )

    def _can_manage_meeting_resume(self):
        """Определяет, может ли специалист добавить или изменить итоги встречи."""
        return bool(
            self.slot
            and self.slot.status in ["started", "completed"]
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
        """Отменяет текущую встречу по инициативе специалиста."""
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
                cancel_reason=form.cleaned_data["cancel_reason"]
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
        """Переносит встречу специалистом на новый слот в его рабочем расписании."""
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
        client_user = self.detail_data.counterpart_user
        specialist_profile = self._get_specialist_profile()
        if client_user is None or specialist_profile is None:
            messages.error(self.request, "Не удалось определить участников встречи для переноса.")
            return redirect(self.get_success_url())

        # 5) Фиксируем тот же тип сессии, что и был
        consultation_type = "couple" if self.event.event_type == "session_couple" else "individual"

        # 6) Выполняем "ПЕРЕНОС"
        try:
            booking_result = reschedule_therapy_session_slot(
                slot=self.slot,
                client_user=client_user,
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

    def _handle_save_meeting_url(self):
        """Сохраняет ссылку на видеовстречу в блоке "Подключение"."""
        if not self._can_manage_meeting_url():
            messages.error(self.request, "Ссылку можно редактировать только до завершения встречи.")
            return redirect(self.get_success_url())

        form = PsychologistTherapySessionDetailsForm(self.request.POST)
        meeting_url = (form.data.get("meeting_url") or "").strip()

        if meeting_url:
            url_field = PsychologistTherapySessionDetailsForm.base_fields["meeting_url"]
            try:
                meeting_url = url_field.clean(meeting_url)
            except Exception as exc:
                messages.error(self.request, str(exc))
                return redirect(self.get_success_url())

        self.slot.meeting_url = meeting_url
        self.slot.full_clean()
        self.slot.save(update_fields=["meeting_url", "updated_at"])

        messages.success(self.request, "Ссылка на видеовстречу сохранена!")

        return redirect(self.get_success_url())

    def _handle_delete_meeting_url(self):
        """Удаляет ссылку на видеовстречу из активной сессии."""
        if not self._can_manage_meeting_url():
            messages.error(self.request, "Удалить ссылку можно только до завершения встречи.")
            return redirect(self.get_success_url())

        self.slot.meeting_url = ""
        self.slot.full_clean()
        self.slot.save(update_fields=["meeting_url", "updated_at"])

        messages.success(self.request, "Ссылка на видеовстречу удалена.")

        return redirect(self.get_success_url())

    def _handle_save_meeting_resume(self):
        """Сохраняет итоги встречи после начала или завершения сессии."""
        if not self._can_manage_meeting_resume():
            messages.error(self.request, "Итоги можно добавить после начала встречи.")
            return redirect(self.get_success_url())

        meeting_resume = (self.request.POST.get("meeting_resume") or "").strip()

        self.slot.meeting_resume = meeting_resume
        self.slot.full_clean()
        self.slot.save(update_fields=["meeting_resume", "updated_at"])

        messages.success(self.request, "Итоги встречи сохранены!")

        return redirect(self.get_success_url())

    def _handle_save_event_description(self):
        """Сохраняет описание события, которое увидят участники встречи."""
        event_description = (self.request.POST.get("event_description") or "").strip()
        self.event.description = event_description
        self.event.full_clean()
        self.event.save(update_fields=["description", "updated_at"])

        messages.success(self.request, "Описание события обновлено!")

        return redirect(self.get_success_url())

    def _get_session_change_reason_label(self):
        """Возвращает заголовок для блока с описанием причины "Отмены" или "Переноса" текущей встречи."""
        if not self.slot or self.slot.status != "cancelled" or not self.slot.cancel_reason:
            return None

        if self.slot.cancel_reason_type == "rescheduled":
            return "Причина переноса встречи"

        return "Причина отмены встречи"

    def _get_rescheduled_event_url(self):
        """Возвращает ссылку на новую следующую встречу после переноса."""
        if not self.slot or self.slot.cancel_reason_type != "rescheduled":
            return None

        # get_latest_rescheduled_descendant() - возвращает актуального потомка события по цепочке previous_event
        rescheduled_event = get_latest_rescheduled_descendant(
            event=self.event,
            viewer_user=self.request.user
        )
        if rescheduled_event is None:
            return None

        return self._get_event_detail_url(event_id=rescheduled_event.id)

    def _get_specialist_profile(self):
        """Возвращает профиль текущего специалиста из shared detail loader для клиентской страницы.

        Бизнес-смысл:
            - текущая страница всегда открывается клиентом;
            - shared loader уже нашел counterpart_user;
            - в клиентском сценарии counterpart = это специалист;
            - поэтому здесь просто безопасно достаем psychologist_profile без повторного поиска участника.
        """
        return getattr(self.request.user, "psychologist_profile", None)

    def _build_matched_topics(self):
        """Собирает совпадающие темы между анкетой клиента и профилем специалиста для detail-screen сессии."""
        client_user = self.detail_data.counterpart_user
        specialist_profile = self._get_specialist_profile()

        if client_user is None or specialist_profile is None:
            return []
        try:
            client_profile = client_user.client_profile
        except Exception:
            return []

        # На detail-странице берем все темы клиента из анкеты без ограничения по preferred_topic_type:
        # эта страница уже не подбирает специалиста по одному сценарию, а показывает итоговое
        # пересечение анкеты клиента с рабочими темами конкретного специалиста
        requested_topic_ids = client_profile.requested_topics.values_list("id", flat=True)

        return list(
            specialist_profile.topics.filter(id__in=requested_topic_ids).order_by("group_name", "name")
        )

    def _create_slot_message(self, form):
        """Создает новое сообщение текущего пользователя внутри активной встречи."""
        slot_message = TimeSlotMessage(
            creator=self.request.user,
            slot=self.slot,
            message=form.cleaned_data["message"]
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

        slot_message = get_object_or_404(TimeSlotMessage, pk=message_id, slot=self.slot, creator=self.request.user)
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
        """Готовит сообщения встречи для общего forum-шаблона.

        Бизнес-смысл:
            - шаблону нужны не сырые ORM-объекты, а уже готовые значения для UX:
                - направление сообщения (слева/справа);
                - можно ли редактировать;
                - нужно ли показывать кнопку "показать все";
                - локальное время сообщения для текущего пользователя.
        """
        if self.slot is None:
            return []

        viewer_timezone = getattr(self.request.user, "timezone", None)
        message_items = []

        for slot_message in self.slot.messages.all():
            local_created_at = timezone.localtime(slot_message.created_at, viewer_timezone)
            local_updated_at = timezone.localtime(slot_message.updated_at, viewer_timezone)
            creator_full_name = f"{slot_message.creator.first_name} {slot_message.creator.last_name}".strip()

            message_items.append(
                {
                    "id": str(slot_message.pk),
                    "comment": slot_message,
                    "message_preview": Truncator(slot_message.message).chars(self.message_length, truncate="..."),
                    "is_long_message": len(slot_message.message) > self.message_length,
                    "is_own_message": slot_message.creator_id == self.request.user.pk,
                    "can_edit": self._can_edit_slot_message(slot_message),
                    "creator_full_name": creator_full_name or slot_message.creator.email,
                    "creator_avatar_url": slot_message.creator.avatar_url,
                    "created_at_display": local_created_at.strftime("%d.%m.%Y %H:%M"),
                    "updated_at_display": local_updated_at.strftime("%d.%m.%Y %H:%M"),
                }
            )

        return message_items
