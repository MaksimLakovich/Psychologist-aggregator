from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from calendar_engine._api.serializers.availability import (
    AvailabilityExceptionSerializer, AvailabilityRuleSerializer)
from calendar_engine.models import AvailabilityException, AvailabilityRule
from core.forms.psychologist.my_account.form_working_schedule import (
    AvailabilityExceptionTimeWindowFormSet, AvailabilityExceptionWebForm,
    AvailabilityRuleTimeWindowFormSet, AvailabilityRuleWebForm, WEEKDAY_LABELS)
from users.mixins.role_required_mixin import PsychologistRequiredMixin


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="post")
class PsychologistWorkingSchedulePageView(PsychologistRequiredMixin, TemplateView):
    """Страница настройки рабочего расписания специалиста.

    В бизнес-терминах здесь есть два уровня управления:
        1) Базовое рабочее правило - это стандартный ритм недели.
        2) Исключения - это временные отклонения от стандартного ритма.

    Такое разделение помогает не путать "как специалист работает обычно" и "что изменилось на конкретные даты".
    """

    template_name = "core/psychologist_pages/my_account/working_schedule.html"
    success_url = reverse_lazy("core:psychologist-working-schedule")

    def get_active_rule(self):
        return (
            AvailabilityRule.objects
            .filter(creator=self.request.user, is_active=True)
            .prefetch_related("time_windows")
            .first()
        )

    def get_active_exceptions(self):
        return (
            AvailabilityException.objects
            .filter(creator=self.request.user, is_active=True)
            .select_related("rule")
            .prefetch_related("time_windows")
            .order_by("exception_start", "created_at")
        )

    def get_archived_rules(self):
        return (
            AvailabilityRule.objects
            .filter(creator=self.request.user, is_active=False)
            .prefetch_related("time_windows")
            .order_by("-created_at")[:5]
        )

    def get_archived_exceptions(self):
        return (
            AvailabilityException.objects
            .filter(creator=self.request.user, is_active=False)
            .prefetch_related("time_windows")
            .order_by("-created_at")[:5]
        )

    def get_rule_form(self, *, data=None):
        return AvailabilityRuleWebForm(data=data)

    def get_rule_windows_formset(self, *, data=None):
        return AvailabilityRuleTimeWindowFormSet(data=data, prefix="rule_windows")

    def get_exception_form(self, *, data=None):
        return AvailabilityExceptionWebForm(data=data)

    def get_exception_windows_formset(self, *, data=None):
        return AvailabilityExceptionTimeWindowFormSet(data=data, prefix="exception_windows")

    @staticmethod
    def _collect_rule_windows(formset):
        """Забираем из formset только реально заполненные рабочие окна.

        Это нужно, чтобы extra-формы и строки, отмеченные на удаление, не попадали в payload сериализатора.
        """
        windows = []
        for form in formset.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            start_time = form.cleaned_data.get("start_time")
            end_time = form.cleaned_data.get("end_time")
            if start_time and end_time:
                windows.append({"start_time": start_time, "end_time": end_time})
        return windows

    @staticmethod
    def _collect_exception_windows(formset):
        windows = []
        for form in formset.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            start_time = form.cleaned_data.get("override_start_time")
            end_time = form.cleaned_data.get("override_end_time")
            if start_time and end_time:
                windows.append({"override_start_time": start_time, "override_end_time": end_time})
        return windows

    @staticmethod
    def _weekday_label(day_number):
        return WEEKDAY_LABELS.get(day_number, str(day_number))

    def _decorate_rule(self, rule):
        """Добавляем объекту удобные UI-поля без изменения модели.

        Это делает шаблон чище: HTML получает уже готовые подписи дней недели,
        а не пытается собирать их через сложную шаблонную логику.
        """
        if rule is None:
            return None
        rule.weekday_labels = [self._weekday_label(day_number) for day_number in (rule.weekdays or [])]
        return rule

    def get_context_data(self, **kwargs):
        """Передаем в HTML как сами формы, так и текущую картину расписания специалиста."""
        context = super().get_context_data(**kwargs)

        context.setdefault("rule_form", self.get_rule_form())
        context.setdefault("rule_windows_formset", self.get_rule_windows_formset())
        context.setdefault("exception_form", self.get_exception_form())
        context.setdefault("exception_windows_formset", self.get_exception_windows_formset())
        context.setdefault("active_schedule_tab", "rule")

        context["title_psychologist_working_schedule_view"] = "Рабочее расписание специалиста в сервисе ОПОРА"
        context["show_sidebar"] = "sidebar"
        context["current_sidebar_key"] = "available-rule"
        context["active_rule"] = self._decorate_rule(self.get_active_rule())
        context["active_exceptions"] = self.get_active_exceptions()
        context["archived_rules"] = [self._decorate_rule(rule) for rule in self.get_archived_rules()]
        context["archived_exceptions"] = self.get_archived_exceptions()
        context["weekday_label_map"] = WEEKDAY_LABELS

        return context

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        action = request.POST.get("schedule_action")

        if action == "create-rule":
            return self.handle_create_rule(request)
        if action == "deactivate-rule":
            return self.handle_deactivate_rule(request)
        if action == "create-exception":
            return self.handle_create_exception(request)
        if action == "deactivate-exception":
            return self.handle_deactivate_exception(request)

        messages.error(
            request,
            "Не удалось определить действие на странице расписания. Повторите попытку из нужного блока формы."
        )
        return redirect(self.success_url)

    @transaction.atomic
    def handle_create_rule(self, request):
        """Создание нового активного рабочего правила.

        Важно для бизнеса: у специалиста может быть только одно активное базовое правило.
        Поэтому при создании нового правила старое мягко архивируется, а не удаляется насовсем.
        """
        rule_form = self.get_rule_form(data=request.POST)
        rule_windows_formset = self.get_rule_windows_formset(data=request.POST)

        if rule_form.is_valid() and rule_windows_formset.is_valid():
            payload = {
                "rule_start": rule_form.cleaned_data["rule_start"],
                "rule_end": rule_form.cleaned_data["rule_end"],
                "weekdays": rule_form.cleaned_data["weekdays"],
                "available_windows": self._collect_rule_windows(rule_windows_formset),
                "session_duration_individual": rule_form.cleaned_data["session_duration_individual"],
                "session_duration_couple": rule_form.cleaned_data["session_duration_couple"],
                "break_between_sessions": rule_form.cleaned_data["break_between_sessions"],
                "minimum_booking_notice_hours": rule_form.cleaned_data["minimum_booking_notice_hours"],
            }

            serializer = AvailabilityRuleSerializer(
                data=payload,
                context={"request": request},
            )

            if serializer.is_valid():
                AvailabilityRule.objects.filter(
                    creator=request.user,
                    is_active=True,
                ).update(is_active=False)

                serializer.save(
                    timezone=getattr(request.user, "timezone", None),
                    is_active=True,
                )
                messages.success(
                    request,
                    "Рабочее расписание сохранено. Именно по этому правилу сервис будет показывать доступные слоты клиентам."
                )
                return redirect(self.success_url)

            for field_name, field_errors in serializer.errors.items():
                rule_form.add_error(None, f"{field_name}: {'; '.join(map(str, field_errors))}")

        messages.error(
            request,
            "Рабочее расписание не сохранено. Исправьте ошибки в датах, днях недели или временных окнах."
        )
        return self.render_to_response(
            self.get_context_data(
                rule_form=rule_form,
                rule_windows_formset=rule_windows_formset,
                active_schedule_tab="rule",
            )
        )

    def handle_deactivate_rule(self, request):
        active_rule = self.get_active_rule()
        if not active_rule:
            messages.error(request, "Активное рабочее расписание не найдено.")
            return redirect(self.success_url)

        active_rule.is_active = False
        active_rule.save(update_fields=["is_active"])

        messages.success(
            request,
            "Активное рабочее расписание закрыто. Пока вы не создадите новое правило, новые слоты для записи показываться не будут."
        )
        return redirect(self.success_url)

    @transaction.atomic
    def handle_create_exception(self, request):
        """Создание исключения из базового рабочего расписания."""
        exception_form = self.get_exception_form(data=request.POST)
        exception_windows_formset = self.get_exception_windows_formset(data=request.POST)
        active_rule = self.get_active_rule()

        if not active_rule:
            messages.error(
                request,
                "Сначала сохраните базовое рабочее расписание, а потом добавляйте исключения."
            )
            return self.render_to_response(
                self.get_context_data(
                    exception_form=exception_form,
                    exception_windows_formset=exception_windows_formset,
                    active_schedule_tab="exception",
                )
            )

        if exception_form.is_valid() and exception_windows_formset.is_valid():
            exception_type = exception_form.cleaned_data["exception_type"]
            override_windows = self._collect_exception_windows(exception_windows_formset)
            if (
                exception_type == "override"
                and not override_windows
            ):
                exception_windows_formset._non_form_errors = exception_windows_formset.error_class(
                    ["Для частичного переопределения добавьте хотя бы одно временное окно."]
                )
            else:
                if exception_type != "override":
                    # Когда специалист выбирает "полностью недоступен", все override-настройки теряют смысл.
                    # Мы сознательно обнуляем их на сервере, чтобы скрытые или ранее введенные значения
                    # не ломали сохранение и не создавали для пользователя лишние ошибки.
                    override_windows = []
                    override_session_duration_individual = None
                    override_session_duration_couple = None
                    override_break_between_sessions = None
                    override_minimum_booking_notice_hours = None
                else:
                    override_session_duration_individual = exception_form.cleaned_data["override_session_duration_individual"]
                    override_session_duration_couple = exception_form.cleaned_data["override_session_duration_couple"]
                    override_break_between_sessions = exception_form.cleaned_data["override_break_between_sessions"]
                    override_minimum_booking_notice_hours = exception_form.cleaned_data["override_minimum_booking_notice_hours"]

                payload = {
                    "rule": active_rule.pk,
                    "exception_start": exception_form.cleaned_data["exception_start"],
                    "exception_end": exception_form.cleaned_data["exception_end"],
                    "reason": exception_form.cleaned_data["reason"],
                    "exception_type": exception_type,
                    "override_available_windows": override_windows,
                    "override_session_duration_individual": override_session_duration_individual,
                    "override_session_duration_couple": override_session_duration_couple,
                    "override_break_between_sessions": override_break_between_sessions,
                    "override_minimum_booking_notice_hours": override_minimum_booking_notice_hours,
                }

                serializer = AvailabilityExceptionSerializer(
                    data=payload,
                    context={"request": request},
                )

                if serializer.is_valid():
                    serializer.save(
                        rule=active_rule,
                        is_active=True,
                    )
                    messages.success(
                        request,
                        "Исключение сохранено. Сервис учтет его поверх базового рабочего расписания."
                    )
                    return redirect(self.success_url)

                for field_name, field_errors in serializer.errors.items():
                    exception_form.add_error(None, f"{field_name}: {'; '.join(map(str, field_errors))}")

        messages.error(
            request,
            "Исключение не сохранено. Проверьте даты, тип исключения и временные окна."
        )
        return self.render_to_response(
            self.get_context_data(
                exception_form=exception_form,
                exception_windows_formset=exception_windows_formset,
                active_schedule_tab="exception",
            )
        )

    def handle_deactivate_exception(self, request):
        exception = get_object_or_404(
            AvailabilityException,
            creator=request.user,
            pk=request.POST.get("exception_id"),
            is_active=True,
        )
        exception.is_active = False
        exception.save(update_fields=["is_active"])

        messages.success(
            request,
            "Исключение закрыто. Базовое рабочее расписание снова действует без этого временного отклонения."
        )
        return redirect(self.success_url)
