from datetime import time

from django import forms
from django.forms import BaseFormSet, formset_factory

from calendar_engine.constants import (AVAILABILITY_EXCEPTION_CHOICES,
                                       EXCEPTION_TYPE_CHOICES,
                                       WEEKDAYS_CHOICES)
from calendar_engine.services import (get_local_date_for_user,
                                      time_windows_have_overlap)


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

    def __init__(self, *args, user=None, **kwargs):
        """Сохраняем пользователя в форме, чтобы при ее создании дата в "today" считалась в его часовом поясе."""
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_weekdays(self):
        """Сохраняем weekdays как список целых чисел, который ожидает модель/сериализатор."""
        return [int(value) for value in self.cleaned_data["weekdays"]]

    def clean(self):
        """Проверяем период действия правила до отправки данных в календарный движок."""
        cleaned_data = super().clean()
        rule_start = cleaned_data.get("rule_start")
        rule_end = cleaned_data.get("rule_end")
        today = get_local_date_for_user(self.user)

        # Тут использую "self.add_error(...)" вместо "raise forms.ValidationError(...)" потому что:
        # self.add_error(...) - когда хотим привязать ошибку к конкретному полю формы;
        # raise forms.ValidationError(...) - когда ошибка относится ко всей форме целиком, а не к одному полю
        if rule_start and rule_start < today:
            self.add_error("rule_start", "Дата начала рабочего расписания не может быть в прошлом")

        if rule_end and rule_end < today:
            self.add_error("rule_end", "Дата окончания рабочего расписания не может быть в прошлом")

        if rule_start and rule_end and rule_start > rule_end:
            self.add_error("rule_end", "Дата окончания не может быть раньше даты начала")

        return cleaned_data


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
        """Проверяем временные окна до отправки данных в календарный движок."""
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if not start_time and not end_time:
            return cleaned_data

        if not start_time or not end_time:
            raise forms.ValidationError("Для рабочего окна нужно заполнить и начало, и окончание")

        if start_time == end_time and start_time != time(0, 0):
            raise forms.ValidationError(
                "Начало и окончание окна могут совпадать только для круглосуточного режима 00:00-00:00"
            )

        if start_time > end_time and end_time != time(0, 0):
            raise forms.ValidationError(
                "Время начала должно быть меньше времени окончания. Если рабочее время переходит через полночь, "
                "создайте два окна: до 00:00 и после 00:00"
            )

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

    def __init__(self, *args, user=None, **kwargs):
        """Сохраняем пользователя, чтобы дата "сегодня" считалась в его часовом поясе."""
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        """Проверяем период действия исключения до отправки данных в календарный движок."""
        cleaned_data = super().clean()
        exception_start = cleaned_data.get("exception_start")
        exception_end = cleaned_data.get("exception_end")
        today = get_local_date_for_user(self.user)

        # Тут использую "self.add_error(...)" вместо "raise forms.ValidationError(...)" потому что:
        # self.add_error(...) - когда хотим привязать ошибку к конкретному полю формы;
        # raise forms.ValidationError(...) - когда ошибка относится ко всей форме целиком, а не к одному полю
        if exception_start and exception_start < today:
            self.add_error("exception_start", "Дата начала исключения не может быть в прошлом")

        if exception_end and exception_end < today:
            self.add_error("exception_end", "Дата окончания исключения не может быть в прошлом")

        if exception_start and exception_end and exception_start > exception_end:
            self.add_error("exception_end", "Дата окончания исключения не может быть раньше даты начала")

        return cleaned_data


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
        """Проверяем временные окна до отправки данных в календарный движок."""
        cleaned_data = super().clean()
        start_time = cleaned_data.get("override_start_time")
        end_time = cleaned_data.get("override_end_time")

        if not start_time and not end_time:
            return cleaned_data

        if not start_time or not end_time:
            raise forms.ValidationError("Для переопределенного окна нужно заполнить и начало, и окончание")

        if start_time == end_time and start_time != time(0, 0):
            raise forms.ValidationError(
                "Начало и окончание окна могут совпадать только для круглосуточного режима 00:00-00:00"
            )

        if start_time > end_time and end_time != time(0, 0):
            raise forms.ValidationError(
                "Время начала должно быть меньше времени окончания. Если переопределенное время переходит через "
                "полночь, создайте два окна: до 00:00 и после 00:00"
            )

        return cleaned_data


class BaseRequiredWindowFormSet(BaseFormSet):
    """FormSet для рабочих окон, где минимум одно корректное окно обязательно.

    Это защищает страницу от пустого правила, которое визуально выглядит созданным,
    но фактически не дает ни одного слота для записи.
    """

    def clean(self):
        """Проверяем минимум одно временное корректное окно создано."""
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
            raise forms.ValidationError("Добавьте хотя бы одно рабочее окно")

        windows = [
            {
                "start_time": form.cleaned_data.get("start_time"),
                "end_time": form.cleaned_data.get("end_time"),
            }
            for form in self.forms
            if hasattr(form, "cleaned_data")
            and not (self.can_delete and form.cleaned_data.get("DELETE"))
            and form.cleaned_data.get("start_time")
            and form.cleaned_data.get("end_time")
        ]

        if time_windows_have_overlap(windows, start_key="start_time", end_key="end_time"):
            raise forms.ValidationError(
                "Нельзя создавать рабочие окна, которые занимают одинаковое время или пересекаются между собой"
            )


class BaseOptionalWindowFormSet(BaseFormSet):
    """FormSet для исключений, где окна могут отсутствовать.

    Например, когда специалист ставит отпуск или больничный и день просто закрывается полностью.
    """

    def clean(self):
        super().clean()

        windows = [
            {
                "override_start_time": form.cleaned_data.get("override_start_time"),
                "override_end_time": form.cleaned_data.get("override_end_time"),
            }
            for form in self.forms
            if hasattr(form, "cleaned_data")
            and not (self.can_delete and form.cleaned_data.get("DELETE"))
            and form.cleaned_data.get("override_start_time")
            and form.cleaned_data.get("override_end_time")
        ]

        if time_windows_have_overlap(
            windows,
            start_key="override_start_time",
            end_key="override_end_time",
        ):
            raise forms.ValidationError(
                "Нельзя переопределять окна так, чтоб они занимали одинаковое время или пересекались между собой"
            )


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
