from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from calendar_engine.models import AvailabilityException, AvailabilityRule
from core.services.topic_groups import build_topics_grouped_by_type
from users._web.forms.edit_psychologist_form import (
    EditPsychologistAccountForm, EditPsychologistProfileForm,
    PsychologistEducationFormSet)
from users.mixins.role_required_mixin import PsychologistRequiredMixin
from users.models import AppUser, Education, Method, Specialisation


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
    allowed_tabs = {"profile", "personal", "education", "expertise"}

    def get_requested_active_tab(self) -> str | None:
        """Возвращает вкладку, которую пользователь явно запросил через GET или POST."""
        requested_tab = self.request.POST.get("active_tab") or self.request.GET.get("tab")
        if requested_tab in self.allowed_tabs:
            return requested_tab
        return None

    def get_user_instance(self) -> AppUser:
        """Возвращает актуальный объект пользователя из БД."""
        # ВАЖНО: здесь используем внутренний кеш потому что:
        #   - в рамках одного открытия страницы этот метод вызывается несколько раз;
        #   - без кеша каждый такой вызов повторно ходил бы в БД за одним и тем же пользователем;
        #   - поэтому первый вызов загружает пользователя, а остальные просто переиспользуют уже полученный объект
        if not hasattr(self, "_cached_user_instance"):
            self._cached_user_instance = AppUser.objects.select_related("psychologist_profile").get(
                pk=self.request.user.pk
            )
        return self._cached_user_instance

    def get_profile_instance(self):
        """Возвращает профессиональный профиль текущего специалиста.

        Для бизнес-логики это главный объект страницы:
            - в нем лежит биография;
            - темы и методы работы;
            - стоимость сессий;
            - фото и другие параметры публичной карточки.
        """
        # ВАЖНО: здесь тоже используем внутренний кеш потому что:
        #   - профиль нужен и для формы, и для контекста, и для сохранения;
        #   - это все еще один и тот же профиль в рамках одного запроса;
        #   - поэтому мы один раз берем его у пользователя и дальше используем повторно
        if not hasattr(self, "_cached_profile_instance"):
            self._cached_profile_instance = self.get_user_instance().psychologist_profile
        return self._cached_profile_instance

    def get_education_queryset(self):
        """Все записи образования текущего специалиста.

        Отдельный queryset нужен как единый источник истины:
            - для показа карточек в шаблоне;
            - для formset при POST;
            - для защиты от случайного доступа к чужим документам.
        """
        # ВАЖНО: здесь тоже используем внутренний кеш потому что:
        #   - страница несколько раз обращается к одному и тому же набору образования;
        #   - без кеша мы бы несколько раз собирали одинаковый queryset;
        #   - так код остается простым: есть один метод и одна точка входа для данных об образовании
        if not hasattr(self, "_cached_education_queryset"):
            self._cached_education_queryset = Education.objects.filter(creator=self.request.user).order_by(
                "-year_start",
                "-created_at",
            )
        return self._cached_education_queryset

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
            - формат работы;
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

    def get_bound_profile_ids(self, profile_form, field_name: str) -> list[str]:
        """Возвращает список выбранных значений для M2M-поля профиля в виде строковых ID.

        Это нужно, чтобы шаблон всегда показывал актуальный выбор:
            - при обычном открытии страницы берем значения из БД;
            - после неудачного сохранения берем значения из bound-формы, чтобы пользователь не терял свой выбор.
        """
        value = profile_form[field_name].value()
        if not value:
            return []
        return [str(item) for item in value]

    def get_active_profile_tab(self, *, account_form, profile_form, education_formset) -> str:
        """Определяет, какую вкладку открыть после проверки данных на сервере.

        СУТЬ:
        если пользователь ошибся в конкретном блоке, система должна вернуть его именно туда, где ошибка произошла,
        а не на первую попавшуюся вкладку.

        Поэтому поведение такое:
            - если ошибка в образовании, пользователь сразу видит вкладку "Образование";
            - если ошибка в темах/методах/специализациях, открываем вкладку "Темы и методы";
            - если ошибка в email/телефоне, открываем вкладку "Персональные данные";
            - в остальных случаях открываем вкладку "Данные профиля".
        """
        if education_formset.non_form_errors() or any(form.errors for form in education_formset.forms):
            return "education"

        expertise_fields = {"specialisations", "methods", "topics"}
        if any(field_name in profile_form.errors for field_name in expertise_fields):
            return "expertise"

        personal_fields = {"email", "phone_number"}
        if any(field_name in account_form.errors for field_name in personal_fields):
            return "personal"

        return "profile"

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
        profile = self.get_profile_instance()

        # Сначала архивируем правила и исключения пользователя, срок действия которых уже истек
        AvailabilityRule.close_expired_for_user(self.request.user)
        AvailabilityException.close_expired_for_user(self.request.user)

        context.setdefault("account_form", self.get_account_form())
        context.setdefault("profile_form", self.get_profile_form())
        context.setdefault("education_formset", self.get_education_formset())

        context["title_edit_psychologist_page_view"] = "Редактирование профиля специалиста в сервисе ОПОРА"
        context["show_sidebar"] = "sidebar"
        context["current_sidebar_key"] = "psychologist-profile-edit"
        context["db_user"] = user
        context["db_profile"] = profile
        context["education_records_count"] = self.get_education_queryset().count()
        context["has_active_working_schedule"] = AvailabilityRule.objects.filter(
            creator=self.request.user,
            is_active=True,
        ).exists()
        context["topics_by_type"] = build_topics_grouped_by_type()
        context["all_methods"] = Method.objects.all().order_by("name")
        context["all_specialisations"] = Specialisation.objects.all().order_by("name")
        context["selected_topics"] = self.get_bound_profile_ids(
            context["profile_form"], "topics"
        )
        context["selected_methods"] = self.get_bound_profile_ids(
            context["profile_form"], "methods"
        )
        context["selected_specialisations"] = self.get_bound_profile_ids(
            context["profile_form"], "specialisations"
        )
        context["psychologist_topics"] = profile.topics.filter(id__in=context["selected_topics"]).order_by(
            "type",
            "group_name",
            "name",
        )
        context["psychologist_methods"] = Method.objects.filter(id__in=context["selected_methods"]).order_by("name")
        context["psychologist_specialisations"] = Specialisation.objects.filter(
            id__in=context["selected_specialisations"]
        ).order_by("name")
        context["has_form_errors"] = bool(
            context["account_form"].errors
            or context["profile_form"].errors
            or context["education_formset"].errors
            or context["education_formset"].non_form_errors()
        )
        requested_get_tab = self.request.GET.get("tab")
        if requested_get_tab not in self.allowed_tabs:
            requested_get_tab = None

        context["active_profile_tab"] = requested_get_tab or self.get_active_profile_tab(
            account_form=context["account_form"],
            profile_form=context["profile_form"],
            education_formset=context["education_formset"],
        )

        return context

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
        post_data = request.POST.copy()

        account_form = self.get_account_form(data=post_data)
        profile_form = self.get_profile_form(data=post_data, files=request.FILES)
        education_formset = self.get_education_formset(data=post_data, files=request.FILES)

        if account_form.is_valid() and profile_form.is_valid() and education_formset.is_valid():
            account_form.save()

            profile = profile_form.save(commit=False)
            profile.user = request.user

            profile.save()
            profile_form.save_m2m()

            # У model formset список deleted_objects появляется только после save(commit=False).
            # Поэтому сначала просим Django собрать итоговые изменения по образованию,
            # а уже потом отдельно удаляем старые записи и сохраняем новые/обновленные.
            education_instances = education_formset.save(commit=False)

            # Удаление сначала, затем сохранение актуальных записей.
            # Так легче гарантировать, что итоговое состояние образования совпадает с тем, что видит пользователь
            for deleted_education in education_formset.deleted_objects:
                deleted_education.delete()

            for education in education_instances:
                education.creator = request.user
                education.save()

            messages.success(
                request,
                "Профиль специалиста обновлен!"
            )
            active_tab = self.get_requested_active_tab()
            if active_tab:
                return redirect(f"{self.success_url}?tab={active_tab}")
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
