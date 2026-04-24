from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import modelformset_factory
from timezone_field import TimeZoneFormField

from users.constants import (CURRENCY_CHOICES, GENDER_CHOICES,
                             LANGUAGE_CHOICES, THERAPY_FORMAT_CHOICES)
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
READONLY_SELECT_CLASS = (
    "block w-full rounded-xl border border-gray-100 bg-gray-100 px-4 py-3 text-lg "
    "text-zinc-500 shadow-sm cursor-not-allowed opacity-100 disabled:opacity-100 "
    "disabled:text-zinc-500 disabled:bg-gray-100 disabled:border-gray-100"
)
TEXTAREA_CLASS = (
    "block min-h-[9rem] w-full rounded-2xl border border-gray-100 bg-white px-4 py-3 text-lg "
    "text-zinc-800 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm transition-all duration-200"
)
FILE_INPUT_CLASS = (
    "block w-full rounded-xl border border-indigo-100 bg-white px-4 py-3 text-sm "
    "text-zinc-600 shadow-sm file:mr-4 file:rounded-xl file:border-0 file:bg-indigo-600 file:px-4 file:py-2 "
    "file:text-sm file:font-semibold file:text-white hover:file:bg-indigo-700"
)
READONLY_TEXTAREA_CLASS = (
    "block min-h-[9rem] w-full rounded-2xl border border-gray-100 bg-gray-100 px-4 py-3 text-lg "
    "text-zinc-500 shadow-sm"
)
READONLY_FILE_INPUT_CLASS = (
    "block w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm "
    "text-zinc-500 shadow-sm file:mr-4 file:rounded-xl file:border-0 file:bg-zinc-300 file:px-4 file:py-2 "
    "file:text-sm file:font-semibold file:text-zinc-700"
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
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    # это служебная метка для JS, чтобы он понимал, какие поля надо переключать между режимами:
                    # "просмотр" / "редактирование"
                    "data-editable-field": "1",
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "placeholder": "Фамилия",
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "autocomplete": "family-name",
                }
            ),
            "age": forms.NumberInput(
                attrs={
                    "placeholder": "Возраст",
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
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
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "autocomplete": "tel",
                }
            ),
            "timezone": forms.Select(
                attrs={
                    "class": READONLY_SELECT_CLASS,
                    "data-view-class": READONLY_SELECT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "style": "-webkit-text-fill-color: rgb(113 113 122);",
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
        self.fields["timezone"].label = "Часовой пояс в котором работаю"

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
        label="Владение языками",
        choices=LANGUAGE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(
            attrs={
                "class": "h-4 w-4 rounded border-zinc-300 text-zinc-400 focus:ring-zinc-400",
                "data-view-class": "h-4 w-4 rounded border-zinc-300 text-zinc-400 focus:ring-zinc-400",
                "data-edit-class": "h-4 w-4 rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500",
                "data-editable-field": "1",
            }
        )
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
            "specialisations",
            "methods",
            "topics",
        )
        widgets = {
            "gender": forms.Select(
                attrs={
                    "class": READONLY_SELECT_CLASS,
                    "data-view-class": READONLY_SELECT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "style": "-webkit-text-fill-color: rgb(113 113 122);",
                }
            ),
            "biography": forms.Textarea(
                attrs={
                    "placeholder": "Расскажите о своем опыте, стиле работы и для кого ваша практика будет полезной",
                    "class": READONLY_TEXTAREA_CLASS,
                    "data-view-class": READONLY_TEXTAREA_CLASS,
                    "data-edit-class": TEXTAREA_CLASS,
                    "data-editable-field": "1",
                    "rows": 6,
                }
            ),
            "photo": forms.FileInput(
                attrs={
                    "class": READONLY_FILE_INPUT_CLASS,
                    "data-view-class": READONLY_FILE_INPUT_CLASS,
                    "data-edit-class": FILE_INPUT_CLASS,
                    "data-photo-upload-field": "1",
                    "accept": ".jpg,.jpeg,.png",
                }
            ),
            "practice_start_year": forms.NumberInput(
                attrs={
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "min": 1900,
                    "max": 2100,
                    "placeholder": "Например, 2015",
                }
            ),
            "therapy_format": forms.Select(
                attrs={
                    "class": READONLY_SELECT_CLASS,
                    "data-view-class": READONLY_SELECT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "style": "-webkit-text-fill-color: rgb(113 113 122);",
                }
            ),
            "price_individual": forms.NumberInput(
                attrs={
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "min": 0,
                    "step": "0.01",
                    "placeholder": "Стоимость индивидуальной сессии",
                }
            ),
            "price_couples": forms.NumberInput(
                attrs={
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "min": 0,
                    "step": "0.01",
                    "placeholder": "Стоимость парной сессии",
                }
            ),
            "price_currency": forms.Select(
                attrs={
                    "class": READONLY_SELECT_CLASS,
                    "data-view-class": READONLY_SELECT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "style": "-webkit-text-fill-color: rgb(113 113 122);",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Убираем help_text и добавляем справочники для выбора значений в определенных полях."""
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.help_text = None

        self.fields["gender"].choices = [("", "Выберите пол"), *GENDER_CHOICES]
        self.fields["therapy_format"].choices = [("", "Выберите формат"), *THERAPY_FORMAT_CHOICES]
        self.fields["price_currency"].choices = [("", "Выберите валюту"), *list(CURRENCY_CHOICES)]
        self.fields["specialisations"].queryset = Specialisation.objects.order_by("name")
        self.fields["methods"].queryset = Method.objects.order_by("name")
        self.fields["topics"].queryset = Topic.objects.order_by("group_name", "name")
        # Для checkbox-групп используем отдельную отрисовку в шаблоне,
        # поэтому класс назначаем контейнеру каждого input через renderer уже в HTML
        if self.instance.pk:
            self.fields["languages"].initial = list(self.instance.languages or [])
        else:
            self.fields["languages"].initial = ["russian"]

    def clean_languages(self):
        """Возвращаем список языков в том формате, который ожидает ArrayField модели.

        Т.е., пользователь на форме отмечает языки, например: "Русский", "Английский". Django после валидации
        складывает выбранные значения в self.cleaned_data["languages"], который содержит набор выбранных значений и
        этот метод берет их и принудительно превращает в обычный Python-список (["russian", "english"]),
        потому что в модели языки хранятся как ArrayField, а ему нужен именно список значений.
        """
        return list(self.cleaned_data.get("languages") or [])

    def clean(self):
        """Проверяем, что у специалиста всегда есть фото профиля:
            - фотографию можно заменить;
            - оставить профиль совсем без фото нельзя.
        """
        cleaned_data = super().clean()
        uploaded_photo = cleaned_data.get("photo")
        existing_photo = getattr(self.instance, "photo", None)

        if not uploaded_photo and not existing_photo:
            self.add_error(
                "photo",
                "Добавьте фотографию профиля. Фото является обязательной частью для публичной карточки")

        return cleaned_data


class PsychologistEducationForm(forms.ModelForm):
    """Форма редактирования одной карточки образования специалиста.

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
            "country": forms.Select(
                attrs={
                    "class": READONLY_SELECT_CLASS,
                    "data-view-class": READONLY_SELECT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "placeholder": "Страна учебного учреждения",
                    "style": "-webkit-text-fill-color: rgb(113 113 122);",
                }
            ),
            "institution": forms.TextInput(
                attrs={
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "placeholder": "Укажите название учебного учреждения",
                }
            ),
            "degree": forms.TextInput(
                attrs={
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "placeholder": "Например: Магистр, Сертификат, Профессиональная переподготовка",
                }
            ),
            "specialisation": forms.TextInput(
                attrs={
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "placeholder": "Специализация или программа обучения",
                }
            ),
            "year_start": forms.NumberInput(
                attrs={
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "min": 1900,
                    "max": 2100,
                    "placeholder": "Год начала обучения",
                }
            ),
            "year_end": forms.NumberInput(
                attrs={
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "min": 1900,
                    "max": 2100,
                    "placeholder": "Год окончания обучения",
                }
            ),
            "document": forms.FileInput(
                attrs={
                    "class": READONLY_FILE_INPUT_CLASS,
                    "data-view-class": READONLY_FILE_INPUT_CLASS,
                    "data-edit-class": FILE_INPUT_CLASS,
                    "data-editable-field": "1",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                    "placeholder": "Скан диплома/сертификата",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Убираем help_text."""
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.help_text = None


# Это способ сказать Django: "создай не одну форму образования, а сразу набор одинаковых форм для модели Education".
# У специалиста может быть не одно образование, а несколько (высшее образование, переподготовка, курс и тд).
# Если бы была одна обычная форма, можно было бы редактировать только одну запись, а так FormSet позволяет работать
# сразу с несколькими карточками образования на одной странице.
# modelformset_factory(...) создает "упаковку из нескольких одинаковых форм" для работы сразу с несколькими
# объектами Education на одной странице
PsychologistEducationFormSet = modelformset_factory(
    Education,
    form=PsychologistEducationForm,
    extra=0,  # Сколько еще пустых форм дополнительно показываем (например можно указать 1 для добавления нового)
    can_delete=True,
)
