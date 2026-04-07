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

    Почему здесь не одна форма, а несколько отдельных блоков:
        1) Базовые данные аккаунта живут в AppUser.
        2) Профессиональные данные живут в PsychologistProfile.
        3) Образование хранится отдельными записями, потому что у специалиста обычно несколько документов.

    Такой подход чуть длиннее по коду, но зато прозрачен для бизнеса и безопасен для дальнейшего развития:
        - можно отдельно менять правила валидации каждого блока;
        - не нужно смешивать аккаунт, публичный профиль и документы в одну большую "магическую" форму.
    """

    template_name = "users/edit_psychologist.html"
    success_url = reverse_lazy("users:web:psychologist-profile-edit")

    def get_user_instance(self) -> AppUser:
        """Берем пользователя заново из БД, чтобы работать с актуальной версией аккаунта."""
        return AppUser.objects.select_related("psychologist_profile").get(pk=self.request.user.pk)

    def get_profile_instance(self):
        """У текущего psychologist всегда ожидается собственный PsychologistProfile."""
        return self.get_user_instance().psychologist_profile

    def get_education_queryset(self):
        """Все записи образования текущего специалиста.

        Отдельный queryset нужен как единый источник истины:
            - для показа карточек в шаблоне;
            - для formset при POST;
            - для защиты от случайного доступа к чужим документам.
        """
        return Education.objects.filter(creator=self.request.user).order_by("-year_start", "-created_at")

    def get_user_form(self, *, data=None):
        return EditPsychologistAccountForm(data=data, instance=self.get_user_instance())

    def get_profile_form(self, *, data=None, files=None):
        return EditPsychologistProfileForm(
            data=data,
            files=files,
            instance=self.get_profile_instance(),
        )

    def get_education_formset(self, *, data=None, files=None):
        return PsychologistEducationFormSet(
            data=data,
            files=files,
            queryset=self.get_education_queryset(),
            prefix="education",
        )

    def get_context_data(self, **kwargs):
        """Формирование контекста страницы редактирования профиля специалиста.

        На уровне HTML нам важно передать не только формы, но и служебные параметры layout:
            - заголовок страницы;
            - признак, что это sidebar-страница psychologist-кабинета;
            - ключ подсветки текущего пункта навигации;
            - текущие данные профиля, чтобы показать статус верификации и краткую сводку.
        """
        context = super().get_context_data(**kwargs)
        user = self.get_user_instance()
        profile = user.psychologist_profile

        context.setdefault("account_form", self.get_user_form())
        context.setdefault("profile_form", self.get_profile_form())
        context.setdefault("education_formset", self.get_education_formset())

        context["title_edit_psychologist_page_view"] = "Редактирование профиля специалиста в сервисе ОПОРА"
        context["show_sidebar"] = "sidebar"
        context["current_sidebar_key"] = "psychologist-profile-edit"
        context["db_user"] = user
        context["db_profile"] = profile
        context["education_records_count"] = self.get_education_queryset().count()

        return context

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Сохраняем все блоки страницы одной транзакцией.

        Для бизнеса это означает простое и понятное поведение:
            - либо весь профиль обновился целиком;
            - либо страница вернулась с ошибками и ничего частично не "пополамилось".
        """
        account_form = self.get_user_form(data=request.POST)
        profile_form = self.get_profile_form(data=request.POST, files=request.FILES)
        education_formset = self.get_education_formset(data=request.POST, files=request.FILES)

        if account_form.is_valid() and profile_form.is_valid() and education_formset.is_valid():
            account_form.save()

            profile = profile_form.save(commit=False)
            profile.user = request.user
            profile.save()
            profile_form.save_m2m()

            # Удаление сначала, затем сохранение актуальных записей.
            # Так легче гарантировать, что итоговое состояние образования совпадает с тем, что видит пользователь.
            for deleted_education in education_formset.deleted_objects:
                deleted_education.delete()

            education_instances = education_formset.save(commit=False)
            for education in education_instances:
                education.creator = request.user
                education.save()

            messages.success(
                request,
                "Профиль специалиста обновлен. Изменения уже используются в кабинете и будут доступны в каталоге."
            )
            return redirect(self.success_url)

        messages.error(
            request,
            "Профиль не сохранен. Проверьте поля с ошибками: система подсветила именно те данные, которые нужно исправить."
        )
        return self.render_to_response(
            self.get_context_data(
                account_form=account_form,
                profile_form=profile_form,
                education_formset=education_formset,
            )
        )
