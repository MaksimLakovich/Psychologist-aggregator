import random
import secrets
import re
from uuid import UUID

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Case, IntegerField, Value, When
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from slugify import slugify

from users.models import PsychologistProfile


class PsychologistCatalogPageView(LoginRequiredMixin, TemplateView):
    """Контроллер на основе TemplateView для отображения страницы *Каталог психологов*.

    Основная логика:
        1) Отображает карточки психологов (только верифицированные и активные).
        2) Использует архитектуру без Django-формы (чистый GET-поток).
        3) Показывает первые 18 карточек и поддерживает кнопку "Показать еще" с догрузкой.
        4) На первом входе в каталог формирует случайный порядок карточек и закрепляет этот порядок
           в рамках текущей сессии/seed, чтобы при пагинации не было дублей и "прыгающего" списка.

    Важно:
        - В этой итерации страница реализует базовый каталог + пагинацию.
        - Расширенная фильтрация (topics/methods/price/age/slots) добавляется следующим этапом.
    """

    template_name = "core/client_pages/my_account/psychologist_catalog.html"

    # Храним константы рядом с вью, чтобы не размазывать критичную конфигурацию по проекту.
    PAGE_SIZE = 18
    CATALOG_SEED_SESSION_KEY = "psychologist_catalog_seed"

    def get_queryset(self):
        """Получение базового QuerySet для каталога психологов.

        Почему именно так:
            1) Фильтруем только активных и верифицированных специалистов
               (бизнес-требование публичного каталога).
            2) Применяем select_related/prefetch_related, чтобы избежать N+1-запросов.
            3) Базовую сортировку оставляем стабильной (по id), а реальную случайность
               применяем безопасно на уровне списка id (Python shuffle + seed).
        """
        return (
            PsychologistProfile.objects
            .filter(is_verified=True, user__is_active=True)
            .select_related("user")
            .prefetch_related("methods", "topics", "specialisations")
            .order_by("id")
        )

    def _build_catalog_seed(self):
        """Определяет seed для случайного порядка карточек.

        Алгоритм:
            - Если seed явно пришел в query-параметре (AJAX "Показать еще"), используем его.
            - Если это первый заход на страницу каталога (обычный GET без page/partial),
              создаем новый seed, чтобы при каждом новом входе порядок был новым.
            - Иначе используем seed из session, чтобы пагинация была стабильной.
        """
        seed_from_query = self.request.GET.get("seed")
        if seed_from_query is not None:
            try:
                return int(seed_from_query)
            except ValueError:
                # Невалидный seed в query не должен ломать страницу.
                pass

        page = self.request.GET.get("page")
        is_partial = self.request.GET.get("partial") == "1"

        # Новый вход на страницу каталога: формируем новый рандомный порядок.
        if not is_partial and (page is None or page == "1"):
            seed = secrets.randbelow(10**9)
            self.request.session[self.CATALOG_SEED_SESSION_KEY] = seed
            return seed

        seed_from_session = self.request.session.get(self.CATALOG_SEED_SESSION_KEY)
        if isinstance(seed_from_session, int):
            return seed_from_session

        # Fallback (если в session seed по какой-то причине отсутствует).
        seed = secrets.randbelow(10**9)
        self.request.session[self.CATALOG_SEED_SESSION_KEY] = seed
        return seed

    @staticmethod
    def _build_profile_slug(profile):
        """Формирует человекочитаемый slug карточки психолога в формате:
        `first-name-last-name-uuid`.

        Почему slug формируется динамически, а не хранится в модели:
            - Не требуется миграция на текущем этапе.
            - UUID в конце гарантирует уникальность даже при совпадающих ФИО.
        """
        full_name = f"{profile.user.first_name} {profile.user.last_name}".strip()
        base_slug = slugify(full_name) or "psychologist"

        return f"{base_slug}-{profile.user.uuid}"

    @staticmethod
    def _build_experience_label(work_experience_years):
        """Формирует корректную подпись для опыта на русском языке.

        Примеры:
            1 -> "Опыт 1 год"
            2 -> "Опыт 2 года"
            5 -> "Опыт 5 лет"
        """
        if work_experience_years is None:
            return "Опыт не указан"

        years = int(work_experience_years)
        rem_100 = years % 100
        rem_10 = years % 10

        if 11 <= rem_100 <= 14:
            suffix = "лет"
        elif rem_10 == 1:
            suffix = "год"
        elif 2 <= rem_10 <= 4:
            suffix = "года"
        else:
            suffix = "лет"

        return f"Опыт {years} {suffix}"

    def _get_catalog_page(self):
        """Собирает страницу каталога с учетом случайного порядка и пагинации.

        Возвращает dict:
            - profiles: список PsychologistProfile для текущей страницы;
            - has_next / next_page_number / current_page_number;
            - total_count;
            - catalog_seed.
        """
        queryset = self.get_queryset()
        catalog_seed = self._build_catalog_seed()

        # 1) Берем только id, чтобы дешево перемешать порядок в памяти.
        profile_ids = list(queryset.values_list("id", flat=True))

        # Отдельно обрабатываем полностью пустой каталог, чтобы не создавать некорректную страницу paginator.page(0).
        if not profile_ids:
            return {
                "profiles": [],
                "has_next": False,
                "next_page_number": None,
                "current_page_number": 1,
                "total_count": 0,
                "catalog_seed": catalog_seed,
            }

        # 2) Перемешиваем детерминированно через seed.
        rng = random.Random(catalog_seed)
        rng.shuffle(profile_ids)

        # 3) Пагинируем уже перемешанный список id.
        paginator = Paginator(profile_ids, self.PAGE_SIZE)
        requested_page = self.request.GET.get("page", 1)

        try:
            page_obj = paginator.page(requested_page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        current_page_ids = list(page_obj.object_list)

        # 4) Возвращаем профили в том же порядке, что и в current_page_ids.
        if current_page_ids:
            ordering = Case(
                *[When(pk=pk, then=Value(pos)) for pos, pk in enumerate(current_page_ids)],
                output_field=IntegerField(),
            )
            profiles = list(
                queryset
                .filter(pk__in=current_page_ids)
                .annotate(_catalog_order=ordering)
                .order_by("_catalog_order")
            )
        else:
            profiles = []

        # Динамически добавляем slug в объект, чтобы шаблон не вычислял эту логику сам.
        for profile in profiles:
            profile.catalog_slug = self._build_profile_slug(profile)
            profile.experience_label = self._build_experience_label(profile.work_experience_years)

        return {
            "profiles": profiles,
            "has_next": page_obj.has_next(),
            "next_page_number": page_obj.next_page_number() if page_obj.has_next() else None,
            "current_page_number": page_obj.number,
            "total_count": paginator.count,
            "catalog_seed": catalog_seed,
        }

    def get_context_data(self, **kwargs):
        """Формирование контекста для HTML-шаблона каталога.

        В контекст передаем:
            - title страницы;
            - параметры боковой навигации;
            - карточки текущей страницы;
            - состояние пагинации для кнопки "Показать еще".
        """
        context = super().get_context_data(**kwargs)
        page_data = self._get_catalog_page()

        context["title_psychologist_catalog_page_view"] = "Каталог психологов на Опора — запись на приём к психологу"

        # Логика управление отображением сайдбара:
        # 1) если пришли из сайдбара, показываем его;
        # 2) и показываем верхнее меню без сайдбара, если открыли не из сайдбара
        from_sidebar = self.request.GET.get("layout") == "sidebar"
        context["show_sidebar"] = from_sidebar

        if not from_sidebar:
            context["menu_variant"] = "without-sidebar"

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "psychologist-catalog"

        return context

    def get(self, request, *args, **kwargs):
        """Обрабатывает 2 режима ответа:

        1) Полная HTML-страница (обычный переход в каталог).
        2) JSON с HTML-фрагментом карточек (AJAX-догрузка по кнопке "Показать еще").
        """
        context = self.get_context_data(**kwargs)

        # partial=1 используется только для асинхронной подгрузки следующей страницы.
        if request.GET.get("partial") == "1":
            cards_html = render_to_string(
                "core/client_pages/my_account/_psychologist_catalog_cards.html",
                {
                    "profiles": context["profiles"],
                },
                request=request,
            )

            return JsonResponse(
                {
                    "status": "ok",
                    "cards_html": cards_html,
                    "has_next": context["has_next"],
                    "next_page_number": context["next_page_number"],
                    "catalog_seed": context["catalog_seed"],
                },
                status=200,
            )

        return self.render_to_response(context)


class PsychologistCatalogDetailPageView(LoginRequiredMixin, TemplateView):
    """Контроллер страницы детального профиля психолога из каталога.

    Страница нужна для перехода из краткой карточки по кнопке "Смотреть полный профиль"
    на отдельный URL вида:
        - psychologist_catalog/anna-ivanova-<uuid>/
    """

    template_name = "core/client_pages/my_account/psychologist_catalog_detail.html"

    @staticmethod
    def _extract_uuid_from_slug(profile_slug):
        """Извлекает UUID из хвоста slug.

        Ожидаемый формат slug: `<name-part>-<uuid>`.
        Если формат некорректен, выбрасываем ValueError и возвращаем 404 в вызывающем коде.
        """
        try:
            # UUID содержит дефисы, поэтому нельзя просто брать фрагмент после последнего "-".
            # Ищем UUID строго в конце строки.
            match = re.search(
                r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$",
                profile_slug,
            )
            if not match:
                raise ValueError("invalid_profile_slug")

            uuid_part = match.group(1)
            return UUID(uuid_part)
        except Exception as exc:
            raise ValueError("invalid_profile_slug") from exc

    @staticmethod
    def _build_profile_slug(profile):
        """Дублируем helper из листинга, чтобы detail-страница могла валидировать canonical slug."""
        full_name = f"{profile.user.first_name} {profile.user.last_name}".strip()
        base_slug = slugify(full_name) or "psychologist"

        return f"{base_slug}-{profile.user.uuid}"

    def get_context_data(self, **kwargs):
        """Формирование контекста детальной страницы психолога."""
        context = super().get_context_data(**kwargs)

        profile_slug = kwargs["profile_slug"]

        try:
            user_uuid = self._extract_uuid_from_slug(profile_slug)
        except ValueError:
            raise Http404("Psychologist not found")

        profile = get_object_or_404(
            PsychologistProfile.objects
            .select_related("user")
            .prefetch_related("methods", "topics", "specialisations"),
            is_verified=True,
            user__is_active=True,
            user__uuid=user_uuid,
        )

        # Доп. защита: если пользователь руками изменил "именную" часть slug,
        # но UUID совпал, делаем мягкую синхронизацию в шаблоне (без редиректа пока).
        profile.catalog_slug = self._build_profile_slug(profile)
        profile.experience_label = PsychologistCatalogPageView._build_experience_label(
            profile.work_experience_years
        )

        context["title_psychologist_catalog_detail_page_view"] = (
            f"{profile.user.first_name} {profile.user.last_name} — профиль психолога"
        )
        context["show_sidebar"] = "sidebar"
        context["current_sidebar_key"] = "psychologist-catalog"
        context["profile"] = profile

        return context
