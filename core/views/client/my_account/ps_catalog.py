import random
import secrets

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Case, IntegerField, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import TemplateView

from core.constants import CARDS_PER_PAGE
from users.models import PsychologistProfile
from users.services.slug import generate_unique_slug


class PsychologistCatalogPageView(LoginRequiredMixin, TemplateView):
    """Контроллер на основе TemplateView для отображения страницы *Каталог психологов*.

    Основная логика:
        1) Отображает карточки психологов (только верифицированные и активные).
        2) Использует архитектуру без Django-формы (чистый GET-поток).
        3) Показывает первые N-карточек и поддерживает кнопку "Показать еще" с догрузкой.
        4) На первом входе в каталог формирует случайный порядок карточек и закрепляет этот порядок
            в рамках текущей сессии, чтобы при пагинации не было дублей и "прыгающего" списка."""

    template_name = "core/client_pages/my_account/psychologist_catalog.html"

    # Храним константы рядом с вью, чтобы не размазывать важную конфигурацию по проекту
    page_size = CARDS_PER_PAGE
    CATALOG_SEED_SESSION_KEY = "psychologist_catalog_seed"

    def get_queryset(self):
        """Получение базового QuerySet для каталога психологов.

        Основная логика:
            1) Фильтруем только активных и верифицированных специалистов.
            2) Применяем select_related/prefetch_related, чтобы избежать N+1-запросов.
            3) Базовую сортировку оставляем стабильной (по id), а реальную случайность применяем безопасно
                на уровне списка id (random.shuffle() + seed).
        "Случайность" - это рандомный вывод ВСЕХ карточек БЕЗ фильтрации при первом открытии страницы, чтоб
        была динамика. Далее мы добавим коэффициент совпадения при наличии фильтрации и ранжированный вывод."""
        return (
            PsychologistProfile.objects
            .filter(is_verified=True, user__is_active=True)
            .select_related("user")
            .prefetch_related("methods", "topics", "specialisations")
            .order_by("id")
        )

    def _build_catalog_seed(self):
        """Определяет seed (источник) для случайного порядка карточек.

        Основная логика:
            - Если seed явно пришел в query-параметре (AJAX "Показать еще"), используем его.
            - Если это первый заход на страницу каталога (обычный GET без page/partial),
              создаем новый seed, чтобы при каждом новом входе порядок был новым.
            - Иначе используем seed из session, чтобы пагинация была стабильной."""
        seed_from_query = self.request.GET.get("seed")
        if seed_from_query is not None:
            try:
                return int(seed_from_query)
            except ValueError:
                # Невалидный seed в query не должен ломать страницу
                pass

        page = self.request.GET.get("page")
        is_partial = self.request.GET.get("partial") == "1"

        # Новый вход на страницу каталога: формируем новый рандомный порядок
        if not is_partial and (page is None or page == "1"):
            seed = secrets.randbelow(10**9)
            self.request.session[self.CATALOG_SEED_SESSION_KEY] = seed
            return seed

        seed_from_session = self.request.session.get(self.CATALOG_SEED_SESSION_KEY)
        if isinstance(seed_from_session, int):
            return seed_from_session

        # Fallback (если в session seed по какой-то причине отсутствует)
        seed = secrets.randbelow(10**9)
        self.request.session[self.CATALOG_SEED_SESSION_KEY] = seed
        return seed

    @staticmethod
    def _build_experience_label(work_experience_years):
        """Формирует корректную подпись/окончание для опыта на русском языке.

        Основная логика:
            - "год" (пример, "Опыт 21 год").
            - "года" (пример, "Опыт 4 года").
            - "лет" (пример, "Опыт 25 лет")."""
        if work_experience_years is None:
            return "Опыт не указан"

        years = int(work_experience_years)
        remainder_100 = years % 100  # Остаток от деления на 100 (последние две цифры)
        remainder_10 = years % 10  # Остаток от деления на 10 (последняя цифра)

        # Числа, заканчивающиеся на 11–14 "remainder_100", всегда требуют слова "лет" (исключение 1)
        if 11 <= remainder_100 <= 14:
            suffix = "лет"
        # Числа, заканчивающиеся на 1 (и это не 11), всегда пишем "год" (пример: 1 год, 21 год, 101 год)
        elif remainder_10 == 1:
            suffix = "год"
        # Числа, заканчивающиеся на 2-4 (и это не 12, 13, 14), всегда пишем "года" (пример: 2 года, 34 года)
        elif 2 <= remainder_10 <= 4:
            suffix = "года"
        # Для всех остальных цифр (5, 6, 7, 8, 9, 0) используется "лет" (пример: 5 лет, 20 лет, 100 лет)
        else:
            suffix = "лет"

        return f"Опыт {years} {suffix}"

    @staticmethod
    def _ensure_profile_slug(profile):
        """Гарантирует наличие slug у профиля психолога.

        Основная логика:
            1) После добавления нового поля slug в модель у части старых записей может быть NULL
                до выполнения миграции/бэкфилла.
            2) Каталог и карточки должны стабильно работать даже в этот переходный период."""
        if profile.slug:
            return

        full_name = f"{profile.user.first_name} {profile.user.last_name}".strip()
        source_value = full_name or profile.user.uuid
        profile.slug = generate_unique_slug(profile, source_value)
        profile.save(update_fields=["slug"])

    def _get_catalog_page(self):
        """Собирает страницу каталога с учетом случайного порядка и пагинации.

        Возвращает dict:
            - profiles: список PsychologistProfile для текущей страницы;
            - has_next / next_page_number / current_page_number;
            - total_count;
            - catalog_seed."""
        queryset = self.get_queryset()
        catalog_seed = self._build_catalog_seed()

        # 1) Берем только id, чтобы дешево перемешать порядок в памяти
        profile_ids = list(queryset.values_list("id", flat=True))

        # Отдельно обрабатываем полностью пустой каталог, чтобы не создавать некорректную страницу paginator.page(0)
        if not profile_ids:
            return {
                "profiles": [],
                "has_next": False,
                "next_page_number": None,
                "current_page_number": 1,
                "total_count": 0,
                "catalog_seed": catalog_seed,
            }

        # 2) Перемешиваем детерминированно через seed
        rng = random.Random(catalog_seed)
        rng.shuffle(profile_ids)

        # 3) Пагинируем уже перемешанный список id
        paginator = Paginator(profile_ids, self.page_size)
        requested_page = self.request.GET.get("page", 1)

        try:
            page_obj = paginator.page(requested_page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        current_page_ids = list(page_obj.object_list)

        # 4) Возвращаем профили в том же порядке, что и в current_page_ids
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

        # Динамически обогащаем объект значениями, которые нужны только для текущего UI
        for profile in profiles:
            self._ensure_profile_slug(profile)
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
            - параметры для сайдбара/меню;
            - карточки текущей страницы;
            - состояние пагинации для кнопки "Показать еще"."""
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

        # ВАЖНО: обязательно добавляем page_data в context.
        # Иначе шаблон не получит profiles/has_next/total_count и карточки не отобразятся
        context.update(page_data)

        return context

    def get(self, request, *args, **kwargs):
        """Обрабатывает 2 режима ответа:

        1) Полная HTML-страница (обычный переход в каталог).
        2) JSON с HTML-фрагментом карточек (AJAX-догрузка по кнопке "Показать еще").
        """
        context = self.get_context_data(**kwargs)

        # partial=1 используется только для асинхронной подгрузки следующей страницы
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


class PsychologistCardDetailPageView(LoginRequiredMixin, TemplateView):
    """Контроллер на основе TemplateView для отображения страницы детального профиля психолога из каталога.
    Страница нужна для перехода из краткой карточки по кнопке "Смотреть полный профиль" на отдельный URL вида:
        - psychologist_catalog/anna-ivanova/ """

    template_name = "core/client_pages/my_account/psychologist_card_detail.html"

    def get_context_data(self, **kwargs):
        """Формирование контекста для HTML-шаблона детальной страницы психолога.
        В контекст передаем:
            - title страницы;
            - данные психолога, включая уже готовый текст для "work_experience_years";
            - параметры для сайдбара/меню."""
        context = super().get_context_data(**kwargs)

        profile_slug = kwargs["profile_slug"]
        profile = get_object_or_404(
            PsychologistProfile.objects
            .select_related("user")
            .prefetch_related("methods", "topics", "specialisations"),
            is_verified=True,
            user__is_active=True,
            slug=profile_slug,
        )
        profile.experience_label = PsychologistCatalogPageView._build_experience_label(
            profile.work_experience_years
        )
        context["profile"] = profile

        context["title_psychologist_catalog_detail_page_view"] = (
            f"{profile.user.first_name} {profile.user.last_name} — профиль психолога"
        )

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
