from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import modelformset_factory
from timezone_field import TimeZoneFormField

from users.constants import (CURRENCY_CHOICES, GENDER_CHOICES,
                             LANGUAGE_CHOICES, THERAPY_FORMAT_CHOICES,
                             WORK_STATUS_CHOICES)
from users.models import (AppUser, Education, Method, PsychologistProfile,
                          Specialisation, Topic)


BASE_INPUT_CLASS = (
    "block w-full rounded-xl border border-gray-100 bg-white px-4 py-3 text-lg "
    "text-zinc-800 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm transition-all duration-200"
)
READONLY_INPUT_CLASS = (
    "block w-full rounded-xl border border-gray-100 bg-gray-100 px-4 py-3 text-lg "
    "text-zinc-500 shadow-sm cursor-not-allowed"
)
TEXTAREA_CLASS = (
    "block min-h-[9rem] w-full rounded-2xl border border-gray-100 bg-white px-4 py-3 text-lg "
    "text-zinc-800 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm transition-all duration-200"
)
FILE_INPUT_CLASS = (
    "block w-full rounded-xl border border-dashed border-indigo-200 bg-indigo-50/60 px-4 py-3 text-sm "
    "text-zinc-600 file:mr-4 file:rounded-lg file:border-0 file:bg-indigo-600 file:px-4 file:py-2 "
    "file:text-sm file:font-semibold file:text-white hover:file:bg-indigo-700"
)
SELECT_MULTIPLE_CLASS = (
    "block w-full rounded-xl border border-gray-100 bg-white px-4 py-3 text-base "
    "text-zinc-800 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm transition-all duration-200"
)


class EditPsychologistAccountForm(forms.ModelForm):
    """Форма редактирования данных аккаунта специалиста.

    Здесь лежат именно персональные данные пользователя как сущности AppUser.
    Это отдельный блок от PsychologistProfile, чтобы в коде было проще понимать:
        - что относится к аккаунту;
        - что относится к публичному профессиональному профилю специалиста.
    """

    class Meta:
        model = AppUser
        fields = ("first_name", "last_name", "age", "email", "phone_number", "timezone")
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "Имя",
                    "class": BASE_INPUT_CLASS,
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "placeholder": "Фамилия",
                    "class": BASE_INPUT_CLASS,
                    "autocomplete": "family-name",
                }
            ),
            "age": forms.NumberInput(
                attrs={
                    "placeholder": "Возраст",
                    "class": BASE_INPUT_CLASS,
                    "min": 18,
                    "max": 120,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "name@email.com",
                    "class": READONLY_INPUT_CLASS,
                    "readonly": "readonly",
                    "autocomplete": "email",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "placeholder": "+7XXXXXXXXXX",
                    "class": BASE_INPUT_CLASS,
                    "autocomplete": "tel",
                }
            ),
            "timezone": forms.Select(
                attrs={
                    "class": BASE_INPUT_CLASS,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Убираем help_text и добавляем пустой вариант для timezone."""
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.help_text = None

        timezone_field = self.fields.get("timezone")
        if isinstance(timezone_field, TimeZoneFormField):
            timezone_choices = list(timezone_field.choices)
            if not timezone_choices or timezone_choices[0][0] != "":
                timezone_field.choices = [("", "Выберите часовой пояс"), *timezone_choices]

        # Дополнительная валидация возраста на уровне формы
        self.fields["age"].validators = [MinValueValidator(18), MaxValueValidator(120)]

    def clean_email(self):
        """Email не редактируется в этой форме: всегда возвращаем исходное значение."""
        if self.instance and self.instance.email:
            return self.instance.email

        return self.cleaned_data.get("email")

    def save(self, commit=True):
        """Сохраняем только разрешенные поля, email не меняем."""
        user = super().save(commit=False)
        user.email = self.instance.email

        if commit:
            user.save(update_fields=["first_name", "last_name", "age", "phone_number", "timezone"])

        return user


class EditPsychologistProfileForm(forms.ModelForm):
    """Форма редактирования данных профессионального профиля специалиста.

    Бизнес-смысл этой формы простой:
        - специалист управляет тем, как он будет выглядеть в каталоге и представлен клиенту;
        - администратор позже сможет отдельно проверять достоверность данных и документов;
        - сама форма не вмешивается в клиентский сценарий и работает только с psychologist-flow.
    """

    languages = forms.MultipleChoiceField(
        label="Языки работы",
        choices=LANGUAGE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    specialisations = forms.ModelMultipleChoiceField(
        label="Специализации",
        queryset=Specialisation.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    methods = forms.ModelMultipleChoiceField(
        label="Методы",
        queryset=Method.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    topics = forms.ModelMultipleChoiceField(
        label="Темы, с которыми работаете",
        queryset=Topic.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = PsychologistProfile
        fields = (
            "gender",
            "biography",
            "photo",
            "practice_start_year",
            "languages",
            "therapy_format",
            "price_individual",
            "price_couples",
            "price_currency",
            "work_status",
            "specialisations",
            "methods",
            "topics",
        )
        widgets = {
            "gender": forms.Select(attrs={"class": BASE_INPUT_CLASS}),
            "biography": forms.Textarea(
                attrs={
                    "placeholder": "Расскажите о своем опыте, стиле работы и для кого ваша практика будет полезной.",
                    "class": TEXTAREA_CLASS,
                    "rows": 6,
                }
            ),
            "photo": forms.ClearableFileInput(attrs={"class": FILE_INPUT_CLASS, "accept": ".jpg,.jpeg,.png"}),
            "practice_start_year": forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 1900, "max": 2100, "placeholder": "Например, 2015"}),
            "therapy_format": forms.Select(attrs={"class": BASE_INPUT_CLASS}),
            "price_individual": forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 0, "step": "0.01", "placeholder": "Стоимость индивидуальной сессии"}),
            "price_couples": forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 0, "step": "0.01", "placeholder": "Стоимость парной сессии"}),
            "price_currency": forms.Select(attrs={"class": BASE_INPUT_CLASS}),
            "work_status": forms.Select(attrs={"class": BASE_INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.help_text = None

        self.fields["gender"].choices = [("", "Выберите пол"), *GENDER_CHOICES]
        self.fields["therapy_format"].choices = [("", "Выберите формат"), *THERAPY_FORMAT_CHOICES]
        self.fields["price_currency"].choices = [("", "Выберите валюту"), *list(CURRENCY_CHOICES)]
        self.fields["work_status"].choices = [("", "Выберите рабочий статус"), *WORK_STATUS_CHOICES]
        self.fields["specialisations"].queryset = Specialisation.objects.order_by("name")
        self.fields["methods"].queryset = Method.objects.order_by("name")
        self.fields["topics"].queryset = Topic.objects.order_by("group_name", "name")

        # Для checkbox-групп используем отдельную отрисовку в шаблоне,
        # поэтому класс назначаем контейнеру каждого input через renderer уже в HTML.
        self.fields["languages"].initial = self.instance.languages if self.instance.pk else ["russian"]

    def clean_languages(self):
        """Возвращаем список языков в том формате, который ожидает ArrayField модели."""
        return list(self.cleaned_data.get("languages") or [])


class PsychologistEducationForm(forms.ModelForm):
    """Одна карточка образования специалиста.

    Мы сохраняем каждую запись отдельно, потому что в реальном бизнес-процессе образование специалиста
    почти всегда состоит из нескольких документов: базовое образование, переподготовка, курсы, сертификаты.
    """

    class Meta:
        model = Education
        fields = (
            "country",
            "institution",
            "degree",
            "specialisation",
            "year_start",
            "year_end",
            "document",
        )
        widgets = {
            "country": forms.Select(attrs={"class": BASE_INPUT_CLASS}),
            "institution": forms.TextInput(attrs={"class": BASE_INPUT_CLASS, "placeholder": "Название учебного учреждения"}),
            "degree": forms.TextInput(attrs={"class": BASE_INPUT_CLASS, "placeholder": "Например: Магистр, Сертификат, Профессиональная переподготовка"}),
            "specialisation": forms.TextInput(attrs={"class": BASE_INPUT_CLASS, "placeholder": "Направление или программа обучения"}),
            "year_start": forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 1900, "max": 2100, "placeholder": "Год начала"}),
            "year_end": forms.NumberInput(attrs={"class": BASE_INPUT_CLASS, "min": 1900, "max": 2100, "placeholder": "Год окончания"}),
            "document": forms.ClearableFileInput(attrs={"class": FILE_INPUT_CLASS, "accept": ".pdf,.jpg,.jpeg,.png"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = None


PsychologistEducationFormSet = modelformset_factory(
    Education,
    form=PsychologistEducationForm,
    extra=1,
    can_delete=True,
)
