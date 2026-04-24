from django import forms
from django.forms import BaseFormSet, formset_factory

from calendar_engine.constants import (AVAILABILITY_EXCEPTION_CHOICES,
                                       EXCEPTION_TYPE_CHOICES,
                                       WEEKDAYS_CHOICES)


BASE_INPUT_CLASS = (
    "block w-full rounded-xl border border-gray-100 bg-white px-4 py-3 text-lg "
    "text-zinc-800 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm transition-all duration-200"
)
TEXTAREA_CLASS = (
    "block min-h-[6rem] w-full rounded-2xl border border-gray-100 bg-white px-4 py-3 text-base "
    "text-zinc-800 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm transition-all duration-200"
)

WEEKDAY_LABELS = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}


class AvailabilityRuleWebForm(forms.Form):
    """Форма верхнего уровня для базового рабочего расписания специалиста.

    Эта форма отвечает не за отдельный слот, а за общие правила недели:
        - в какие дни специалист работает;
        - когда правило начинает действовать;
        - какова длительность сессий и паузы.
    """

    rule_start = forms.DateField(
        label="Дата начала",
        widget=forms.DateInput(attrs={"class": BASE_INPUT_CLASS, "type": "date"}),
    )
    rule_end = forms.DateField(
        label="Дата окончания",
        required=False,
        widget=forms.DateInput(attrs={"class": BASE_INPUT_CLASS, "type": "date"}),
    )
    weekdays = forms.MultipleChoiceField(
        label="Рабочие дни",
        choices=[(str(value), WEEKDAY_LABELS.get(value, label)) for value, label in WEEKDAYS_CHOICES],
        widget=forms.CheckboxSelectMultiple,
    )
    session_duration_individual = forms.IntegerField(
        label="Длительность индивидуальной сессии (мин.)",
        min_value=1,
        initial=50,
        widget=forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 1}),
    )
    session_duration_couple = forms.IntegerField(
        label="Длительность парной сессии (мин.)",
        min_value=1,
        initial=90,
        widget=forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 1}),
    )
    break_between_sessions = forms.IntegerField(
        label="Перерыв между сессиями (мин.)",
        min_value=0,
        initial=10,
        widget=forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 0}),
    )
    minimum_booking_notice_hours = forms.IntegerField(
        label="Минимальное время до записи (часы)",
        min_value=0,
        initial=1,
        widget=forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 0}),
    )

    def clean_weekdays(self):
        """Сохраняем weekdays как список целых чисел, который ожидает модель/сериализатор."""
        return [int(value) for value in self.cleaned_data["weekdays"]]


class AvailabilityRuleTimeWindowWebForm(forms.Form):
    """Одно рабочее окно внутри дня, например с 09:00 до 13:00."""

    start_time = forms.TimeField(
        label="Начало рабочего окна",
        required=False,
        widget=forms.TimeInput(attrs={"class": BASE_INPUT_CLASS, "type": "time"}),
    )
    end_time = forms.TimeField(
        label="Окончание рабочего окна",
        required=False,
        widget=forms.TimeInput(attrs={"class": BASE_INPUT_CLASS, "type": "time"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if not start_time and not end_time:
            return cleaned_data

        if not start_time or not end_time:
            raise forms.ValidationError("Для рабочего окна нужно заполнить и начало, и окончание.")

        return cleaned_data


class AvailabilityExceptionWebForm(forms.Form):
    """Форма исключения из рабочего расписания.

    Это отдельный слой поверх базового правила. Его задача простая:
        - либо полностью закрыть период;
        - либо временно переопределить обычный график.
    """

    exception_start = forms.DateField(
        label="Дата начала",
        widget=forms.DateInput(attrs={"class": BASE_INPUT_CLASS, "type": "date"}),
    )
    exception_end = forms.DateField(
        label="Дата окончания",
        widget=forms.DateInput(attrs={"class": BASE_INPUT_CLASS, "type": "date"}),
    )
    reason = forms.ChoiceField(
        label="Причина исключения",
        choices=[("", "Выберите причину"), *AVAILABILITY_EXCEPTION_CHOICES],
        widget=forms.Select(attrs={"class": BASE_INPUT_CLASS}),
    )
    exception_type = forms.ChoiceField(
        label="Как именно применить исключение",
        choices=[("", "Выберите тип"), *EXCEPTION_TYPE_CHOICES],
        widget=forms.Select(attrs={"class": BASE_INPUT_CLASS, "data-exception-type-select": "1"}),
    )
    override_session_duration_individual = forms.IntegerField(
        label="Новая длительность индивидуальной сессии, минут",
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 1}),
    )
    override_session_duration_couple = forms.IntegerField(
        label="Новая длительность парной сессии, минут",
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 1}),
    )
    override_break_between_sessions = forms.IntegerField(
        label="Новый перерыв между сессиями, минут",
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 0}),
    )
    override_minimum_booking_notice_hours = forms.IntegerField(
        label="Новый минимальный запас времени до записи, часов",
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 0}),
    )


class AvailabilityExceptionTimeWindowWebForm(forms.Form):
    """Одно переопределенное рабочее окно на период исключения."""

    override_start_time = forms.TimeField(
        label="Новое начало окна",
        required=False,
        widget=forms.TimeInput(attrs={"class": BASE_INPUT_CLASS, "type": "time"}),
    )
    override_end_time = forms.TimeField(
        label="Новое окончание окна",
        required=False,
        widget=forms.TimeInput(attrs={"class": BASE_INPUT_CLASS, "type": "time"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("override_start_time")
        end_time = cleaned_data.get("override_end_time")

        if not start_time and not end_time:
            return cleaned_data

        if not start_time or not end_time:
            raise forms.ValidationError("Для переопределенного окна нужно заполнить и начало, и окончание.")

        return cleaned_data


class BaseRequiredWindowFormSet(BaseFormSet):
    """FormSet для рабочих окон, где минимум одно корректное окно обязательно.

    Это защищает страницу от пустого правила, которое визуально выглядит созданным,
    но фактически не дает ни одного слота для записи.
    """

    def clean(self):
        super().clean()
        has_window = False

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if self.can_delete and form.cleaned_data.get("DELETE"):
                continue
            if form.cleaned_data.get("start_time") and form.cleaned_data.get("end_time"):
                has_window = True

        if not has_window:
            raise forms.ValidationError("Добавьте хотя бы одно рабочее окно.")


class BaseOptionalWindowFormSet(BaseFormSet):
    """FormSet для исключений, где окна могут отсутствовать.

    Например, когда специалист ставит отпуск или больничный и день просто закрывается полностью.
    """


AvailabilityRuleTimeWindowFormSet = formset_factory(
    AvailabilityRuleTimeWindowWebForm,
    formset=BaseRequiredWindowFormSet,
    extra=1,
    can_delete=True,
)

AvailabilityExceptionTimeWindowFormSet = formset_factory(
    AvailabilityExceptionTimeWindowWebForm,
    formset=BaseOptionalWindowFormSet,
    extra=1,
    can_delete=True,
)
