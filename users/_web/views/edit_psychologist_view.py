from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from users._web.forms.edit_psychologist_form import (
    EditPsychologistAccountForm, EditPsychologistProfileForm,
    PsychologistEducationFormSet)
from users.mixins.role_required_mixin import PsychologistRequiredMixin
from users.models import AppUser, Education


@method_decorator(ratelimit(key="ip", rate="5/m", block=True), name="post")
class EditPsychologistProfilePageView(PsychologistRequiredMixin, TemplateView):
    """Web-страница для редактирования профиля специалиста.

    Логика страницы простая:
        1) Специалист открывает один экран и видит весь свой профиль целиком.
        2) Система делит данные на несколько самостоятельных блоков:
            - аккаунт пользователя;
            - профессиональный профиль;
            - образование и документы.
        3) При сохранении все эти блоки обрабатываются вместе, чтобы пользователь не получил
           "половину обновленного" профиля.

    Такой подход немного длиннее по коду, но лучше для продукта:
        - бизнесу проще понимать, где какие данные живут;
        - легче развивать страницу без скрытых побочных эффектов;
        - меньше риск случайно смешать публичные данные, личные данные и документы.
    """

    template_name = "users/edit_psychologist.html"
    success_url = reverse_lazy("users:web:psychologist-profile-edit")

    def get_user_instance(self) -> AppUser:
        """Возвращает актуальный объект пользователя из БД.

        Это нужно, чтобы страница всегда работала с "живыми" данными из БД, а не со старой копией объекта из request.
        """
        return AppUser.objects.select_related("psychologist_profile").get(pk=self.request.user.pk)

    def get_profile_instance(self):
        """Возвращает профессиональный профиль текущего специалиста.

        Для бизнес-логики это главный объект страницы:
            - в нем лежит биография;
            - темы и методы работы;
            - стоимость сессий;
            - фото и другие параметры публичной карточки.
        """
        return self.get_user_instance().psychologist_profile

    def get_education_queryset(self):
        """Все записи образования текущего специалиста.

        Отдельный queryset нужен как единый источник истины:
            - для показа карточек в шаблоне;
            - для formset при POST;
            - для защиты от случайного доступа к чужим документам.
        """
        return Education.objects.filter(creator=self.request.user).order_by("-year_start", "-created_at")

    def get_account_form(self, *, data=None):
        """Собирает форму с базовыми данными аккаунта специалиста. Отвечает за данные:
            - имя;
            - фамилию;
            - возраст;
            - телефон;
            - часовой пояс.
        """
        return EditPsychologistAccountForm(data=data, instance=self.get_user_instance())

    def get_profile_form(self, *, data=None, files=None):
        """Собирает форму профессионального профиля специалиста. Отвечает за данные:
            - биография;
            - рабочий статус;
            - стоимость;
            - темы, методы и другие параметры публичной карточки.
        """
        return EditPsychologistProfileForm(
            data=data,
            files=files,
            instance=self.get_profile_instance(),
        )

    def get_education_formset(self, *, data=None, files=None):
        """Собирает набор форм для образования специалиста.

        Здесь используется не одна форма, а formset, потому что у одного специалиста
        обычно несколько записей об обучении: базовое образование, курсы, сертификаты и так далее.
        """
        return PsychologistEducationFormSet(
            data=data,
            files=files,
            queryset=self.get_education_queryset(),
            prefix="education",
        )

    def get_context_data(self, **kwargs):
        """Формирование контекста страницы редактирования профиля специалиста.

        На уровне HTML странице нужны не только формы, но и вспомогательные данные:
            - заголовок страницы;
            - параметры для боковой навигации;
            - текущие данные пользователя и профиля;
            - флаг, есть ли ошибки;
            - подсказка, какую вкладку открыть после неудачного сохранения.
        """
        context = super().get_context_data(**kwargs)
        user = self.get_user_instance()
        profile = user.psychologist_profile

        context.setdefault("account_form", self.get_account_form())
        context.setdefault("profile_form", self.get_profile_form())
        context.setdefault("education_formset", self.get_education_formset())

        context["title_edit_psychologist_page_view"] = "Редактирование профиля специалиста в сервисе ОПОРА"
        context["show_sidebar"] = "sidebar"
        context["current_sidebar_key"] = "psychologist-profile-edit"
        context["db_user"] = user
        context["db_profile"] = profile
        context["education_records_count"] = self.get_education_queryset().count()
        context["has_form_errors"] = bool(
            context["account_form"].errors
            or context["profile_form"].errors
            or context["education_formset"].errors
            or context["education_formset"].non_form_errors()
        )
        context["active_profile_tab"] = self.get_active_profile_tab(
            profile_form=context["profile_form"],
            education_formset=context["education_formset"],
        )

        return context

    def get_active_profile_tab(self, *, profile_form, education_formset) -> str:
        """Определяет, какую вкладку открыть после проверки данных на сервере.

        СУТЬ:
        если пользователь ошибся в конкретном блоке, система должна вернуть его именно туда, где ошибка произошла,
        а не на первую попавшуюся вкладку.

        Поэтому поведение такое:
            - если ошибка в образовании, пользователь сразу видит вкладку "Образование" - education_formset;
            - если ошибка в темах/методах/языках, сразу открываем профильную вкладку - profile_form;
            - в остальных случаях оставляем стартовую вкладку с личными данными - это account_form.
        """
        if education_formset.non_form_errors() or any(form.errors for form in education_formset.forms):
            return "education"

        expertise_fields = {"languages", "specialisations", "methods", "topics"}
        if any(field_name in profile_form.errors for field_name in expertise_fields):
            return "expertise"

        return "personal"

    def get(self, request, *args, **kwargs):
        """Обрабатывает обычное открытие страницы через GET-запрос:
            - открыть страницу;
            - увидеть текущие данные аккаунта/профиля;
            - при необходимости перейти в режим редактирования.
        """
        return self.render_to_response(self.get_context_data())

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Сохраняем новые данные при редактировании аккаунта/профиля одной транзакцией:
            - либо весь профиль обновился целиком;
            - либо страница вернулась с ошибками и ничего не сохранилось частично.
        """
        account_form = self.get_account_form(data=request.POST)
        profile_form = self.get_profile_form(data=request.POST, files=request.FILES)
        education_formset = self.get_education_formset(data=request.POST, files=request.FILES)

        if account_form.is_valid() and profile_form.is_valid() and education_formset.is_valid():
            account_form.save()

            profile = profile_form.save(commit=False)
            profile.user = request.user

            # Фото профиля управляется прямо на этой странице:
            # - если пользователь отметил "Удалить текущее фото" и не загрузил новое, очищаем изображение;
            # - если загружен новый файл, Django сам подставит его в поле photo через ModelForm
            if profile_form.cleaned_data.get("remove_photo") and not profile_form.cleaned_data.get("photo"):
                if profile.photo:
                    profile.photo.delete(save=False)
                profile.photo = None

            profile.save()
            profile_form.save_m2m()

            # Удаление сначала, затем сохранение актуальных записей.
            # Так легче гарантировать, что итоговое состояние образования совпадает с тем, что видит пользователь
            for deleted_education in education_formset.deleted_objects:
                deleted_education.delete()

            education_instances = education_formset.save(commit=False)
            for education in education_instances:
                education.creator = request.user
                education.save()

            messages.success(
                request,
                "Профиль специалиста обновлен!"
            )
            return redirect(self.success_url)

        messages.error(
            request,
            "Профиль не сохранен. Проверьте ошибки: система подсветила те данные, которые нужно исправить."
        )
        return self.render_to_response(
            self.get_context_data(
                account_form=account_form,
                profile_form=profile_form,
                education_formset=education_formset,
            )
        )
