import random

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Case, IntegerField, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from core.constants import CARDS_PER_PAGE
from core.services.experience_label import build_experience_label
from users.models import PsychologistProfile
from users.services.slug import generate_unique_slug


@method_decorator(ratelimit(key="user_or_ip", rate="60/m", block=True), name="get")
class PsychologistCatalogPageView(LoginRequiredMixin, TemplateView):
    """Контроллер на основе TemplateView для отображения страницы *Каталог психологов*.

    Основная логика:
        1) Отображает карточки психологов (только верифицированные и активные).
        2) Использует архитектуру без Django-формы (чистый GET-поток).
        3) Показывает первые N-карточек и поддерживает кнопку "Показать еще" с догрузкой.
        4) На первом входе в каталог формирует случайный порядок карточек и закрепляет этот порядок
            в рамках текущей сессии через "ключ случайного порядка", чтобы при пагинации
            не было дублей и "прыгающего" списка."""

    template_name = "core/client_pages/my_account/psychologist_catalog.html"

    # Храним константы рядом с вью, чтобы не размазывать важную конфигурацию по проекту
    page_size = CARDS_PER_PAGE
    # Техническое имя ключа в session. Тут хранится число, которое определяет
    # стабильный случайный порядок/набор карточек на время сессии пользователя
    CATALOG_RANDOM_ORDER_SESSION_KEY = "psychologist_catalog_random_order_key"
    # Техническое имя ключа в session для режима отображения каталога.
    # Возможные значения: "sidebar" / "menu".
    CATALOG_LAYOUT_MODE_SESSION_KEY = "psychologist_catalog_layout_mode"

    def get_queryset(self):
        """Получение базового QuerySet для каталога психологов.

        Основная логика:
            1) Фильтруем только активных и верифицированных специалистов.
            2) Применяем select_related/prefetch_related, чтобы избежать N+1-запросов.
            3) Базовую сортировку оставляем стабильной (по id), а реальную случайность применяем безопасно
                на уровне списка id (random.shuffle() + ключ случайного порядка).

        "Случайность" - это рандомный вывод ВСЕХ карточек БЕЗ фильтрации при первом открытии страницы, чтоб
        была динамика. Далее мы добавим коэффициент совпадения при наличии фильтрации и ранжированный вывод."""
        return (
            PsychologistProfile.objects
            .filter(is_verified=True, user__is_active=True)
            .select_related("user")
            .prefetch_related("methods", "topics", "specialisations")
            .order_by("id")
        )

    @staticmethod
    def _profile_slug(profile):
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

    def _get_or_create_random_order_key(self):
        """Определяет "ключ случайного порядка" для карточек каталога.

        Основная логика:
            - Если ключ явно пришел в query-параметре (AJAX "Показать еще"), используем его.
            - Если это первый заход на страницу каталога (обычный GET без page/partial), то создаем новый ключ,
                чтобы при каждом новом входе порядок был новым.
            - Иначе используем ключ из session, чтобы пагинация была стабильной.

        Почему это важно:
            - page=1, page=2, page=3 должны работать с ОДНИМ и тем же порядком карточек (чтоб случайно не показывать
                одних и тех же психологов и на page=1 и на page=2 и так далее).
            - Тогда "Показать еще" не покажет дубли и не пропустит специалистов."""
        order_key_from_query = self.request.GET.get("order_key")

        if order_key_from_query is not None:
            try:
                return int(order_key_from_query)
            except ValueError:
                # Невалидный ключ в query не должен ломать страницу
                pass

        page = self.request.GET.get("page")
        is_partial = self.request.GET.get("partial") == "1"

        # Новый вход на страницу каталога: формируем новый случайный порядок
        if not is_partial and (page is None or page == "1"):
            random_order_key = random.randrange(10**9)
            self.request.session[self.CATALOG_RANDOM_ORDER_SESSION_KEY] = random_order_key
            return random_order_key

        order_key_from_session = self.request.session.get(self.CATALOG_RANDOM_ORDER_SESSION_KEY)
        if isinstance(order_key_from_session, int):
            return order_key_from_session

        # Fallback (если в session ключ по какой-то причине отсутствует)
        random_order_key = random.randrange(10**9)
        self.request.session[self.CATALOG_RANDOM_ORDER_SESSION_KEY] = random_order_key
        return random_order_key

    def _resolve_layout_mode(self):
        """Определяет режим отображения каталога: через сайдбар или через верхнее меню.

        Возвращает:
            - "sidebar" -> нужно показывать левую навигацию;
            - "menu" -> страница рендерится без левого сайдбара.

        Приоритет источников:
            1) Явный query-параметр layout (например, ?layout=sidebar).
            2) Для AJAX/пагинации без layout берем значение из session.
            3) Для обычного первого входа без layout считаем, что это режим "menu".

        Почему нужен session fallback:
            - В запросах "Показать еще" layout может не прийти по разным причинам
              (кеш статики, устаревший JS, ручной вызов URL), но мы обязаны сохранить
              единый режим интерфейса до конца текущей сессии каталога."""
        layout_from_query = self.request.GET.get("layout")
        if layout_from_query in {"sidebar", "menu"}:
            self.request.session[self.CATALOG_LAYOUT_MODE_SESSION_KEY] = layout_from_query
            return layout_from_query

        is_partial = self.request.GET.get("partial") == "1"
        requested_page = self.request.GET.get("page")

        # Для первого полного входа без явного layout фиксируем "menu",
        # чтобы не подтягивать случайно старый режим из прошлых переходов.
        if not is_partial and (requested_page is None or requested_page == "1"):
            self.request.session[self.CATALOG_LAYOUT_MODE_SESSION_KEY] = "menu"
            return "menu"

        layout_from_session = self.request.session.get(self.CATALOG_LAYOUT_MODE_SESSION_KEY)
        if layout_from_session in {"sidebar", "menu"}:
            return layout_from_session

        return "menu"

    def _build_catalog_page_data(self):
        """Собирает данные текущей страницы каталога (page=1 / page=2 / ...).

        Возвращает dict:
            - profiles: список PsychologistProfile для текущей страницы;
            - has_next / next_page_number / current_page_number;
            - total_count;
            - random_order_key.

        Техническая логика (простыми словами):
            1) Берем id всех подходящих психологов из БД.
            2) Перемешиваем эти id по "ключу случайного порядка".
            3) Берем только нужный кусок страницы (например, 1-18 или 19-36).
            4) Вторым запросом в БД забираем данные только по этим id."""
        queryset = self.get_queryset()
        random_order_key = self._get_or_create_random_order_key()

        # 1) Берем только id, чтобы дешево перемешать порядок в памяти
        profile_ids = list(queryset.values_list("id", flat=True))

        # Отдельно обрабатываем полностью пустой каталог, чтобы не создавать некорректную страницу paginator.page(0)
        if not profile_ids:
            return {
                "profiles": [],
                "has_next": False,
                "next_page_number": None,
                "current_page_number": 1,
                "total_pages": 0,
                "total_count": 0,
                "random_order_key": random_order_key,
            }

        # 2) Перемешиваем детерминированно через "ключ случайного порядка"
        rng = random.Random(random_order_key)
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

        # Для сценария "возврат из детальной карточки в каталог":
        # если указан restore=1 и page>1, то нужно вернуть НЕ только page=2,
        # а всю ленту от начала и до конца этой страницы (1..2, 1..3 и т.д.),
        # чтобы пользователь визуально оказался в том же месте списка.
        restore_mode = self.request.GET.get("restore") == "1" and self.request.GET.get("partial") != "1"
        if restore_mode and page_obj.number > 1:
            end_index = page_obj.end_index()
            current_page_ids = profile_ids[:end_index]
        else:
            current_page_ids = list(page_obj.object_list)

        # 4) Возвращаем профили в том же порядке, что и в current_page_ids
        # current_page_ids - это список id текущей страницы (например, page=2) в нужном порядке после перемешивания.
        # Например: current_page_ids = [42, 7, 19]. Если сделать просто: queryset.filter(pk__in=current_page_ids), то
        # БД вернет записи в своем порядке (часто по id: 7, 19, 42), а нам нужен порядок 42, 7, 19. Вот эту задачу
        # решает код ниже.

        # УПРОЩЕННЫЙ ВАРИАНТ КОДА: конструкцию можно описать в развернутом виде вот так:
        # # Шаг 1. Создаем пустой список условий для SQL-конструкции CASE ... WHEN ...
        # order_conditions = []
        # # Шаг 2. Проходим по id текущей страницы и запоминаем их позицию
        # # Пример current_page_ids = [42, 7, 19]
        # # Тогда пары будут: (0,42), (1,7), (2,19)
        # for position, profile_id in enumerate(current_page_ids):
        #     order_conditions.append(
        #         When(pk=profile_id, then=Value(position))
        #     )
        # # Шаг 3. Собираем итоговое выражение:
        # # CASE
        # #   WHEN pk=42 THEN 0
        # #   WHEN pk=7  THEN 1
        # #   WHEN pk=19 THEN 2
        # # END
        # ordering = Case(
        #     *order_conditions,
        #     output_field=IntegerField(),
        # )
        if current_page_ids:
            # enumerate - дает пары: (0, 42), (1, 7), (2, 19), то есть “какая позиция у каждого id”
            # Case - создает SQL-правило: если pk=42 то _catalog_order=0, если pk=7 то _catalog_order=1 и т.д.
            ordering = Case(
                *[When(pk=pk, then=Value(pos)) for pos, pk in enumerate(current_page_ids)],
                output_field=IntegerField(),
            )
            profiles = list(
                queryset
                .filter(pk__in=current_page_ids)
                .annotate(_catalog_order=ordering)  # annotate - добавляет это вычисленное поле к каждой записи
                .order_by("_catalog_order")  # order_by - сортирует именно по этой позиции и получаем [42, 7, 19]
            )
        else:
            profiles = []

        # Динамически обогащаем объект значениями, которые нужны только для текущего UI
        for profile in profiles:
            self._profile_slug(profile)
            profile.experience_label = build_experience_label(profile.work_experience_years)

        return {
            "profiles": profiles,
            "has_next": page_obj.has_next(),
            "next_page_number": page_obj.next_page_number() if page_obj.has_next() else None,
            "current_page_number": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "random_order_key": random_order_key,
        }

    def get_context_data(self, **kwargs):
        """Формирование контекста для HTML-шаблона каталога.

        В контекст передаем:
            - title страницы;
            - параметры для сайдбара/меню;
            - карточки текущей страницы;
            - состояние пагинации для кнопки "Показать еще"."""
        context = super().get_context_data(**kwargs)
        page_data = self._build_catalog_page_data()

        context["title_psychologist_catalog_page_view"] = "Каталог психологов на Опора — запись на приём к психологу"

        # Логика управления отображением сайдбара.
        # Используем единый layout_mode, чтобы одинаково работать для page=1 и page=2+.
        layout_mode = self._resolve_layout_mode()
        context["layout_mode"] = layout_mode
        context["show_sidebar"] = layout_mode == "sidebar"
        if layout_mode != "sidebar":
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
        2) JSON с HTML-фрагментом карточек (AJAX-догрузка по кнопке "Показать еще")."""
        context = self.get_context_data(**kwargs)

        # partial=1 используется только для асинхронной подгрузки следующей страницы
        if request.GET.get("partial") == "1":
            cards_html = render_to_string(
                "core/client_pages/my_account/short_cards.html",
                {
                    "profiles": context["profiles"],
                    # ВАЖНО: для догружаемых карточек обязательно передаем layout_mode,
                    # иначе у ссылок карточек может потеряться корректный параметр layout.
                    "layout_mode": context["layout_mode"],
                    "show_sidebar": context["show_sidebar"],
                },
                request=request,
            )

            return JsonResponse(
                {
                    "status": "ok",
                    "cards_html": cards_html,
                    "has_next": context["has_next"],
                    "next_page_number": context["next_page_number"],
                    "random_order_key": context["random_order_key"],
                },
                status=200,
            )

        return self.render_to_response(context)


class PsychologistCardDetailPageView(LoginRequiredMixin, TemplateView):
    """Контроллер на основе TemplateView для отображения страницы детального профиля психолога из каталога.
    Страница нужна для перехода из краткой карточки по кнопке "Смотреть полный профиль" на отдельный URL вида:
        - psychologist_catalog/anna-ivanova/ """

    template_name = "core/client_pages/my_account/psychologist_card_detail.html"

    CATALOG_LAYOUT_MODE_SESSION_KEY = PsychologistCatalogPageView.CATALOG_LAYOUT_MODE_SESSION_KEY

    def _resolve_layout_mode(self):
        """Определяет режим отображения детальной карточки психолога.

        Приоритет:
            1) Явный query-параметр layout.
            2) Значение из session, сохраненное на странице каталога.
            3) Режим по умолчанию "menu".

        Такой подход гарантирует, что кнопка "Назад в каталог" вернет пользователя
        в тот же визуальный режим (с сайдбаром или без него)."""
        layout_from_query = self.request.GET.get("layout")
        if layout_from_query in {"sidebar", "menu"}:
            self.request.session[self.CATALOG_LAYOUT_MODE_SESSION_KEY] = layout_from_query
            return layout_from_query

        layout_from_session = self.request.session.get(self.CATALOG_LAYOUT_MODE_SESSION_KEY)
        if layout_from_session in {"sidebar", "menu"}:
            return layout_from_session

        return "menu"

    @staticmethod
    def _build_catalog_back_url(layout_mode):
        """Собирает базовую ссылку "Назад в каталог" для non-JS fallback.

        ВАЖНО:
            - Основное восстановление позиции/страницы теперь делает фронтенд через sessionStorage
              (см. psychologist_catalog.js + psychologist_catalog_detail.js).
            - Серверный fallback оставляем минимальным и предсказуемым:
              возвращаем в каталог с тем же layout (sidebar/menu)."""
        base_url = reverse("core:psychologist-catalog")
        return f"{base_url}?layout={layout_mode}"

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
        profile.experience_label = build_experience_label(profile.work_experience_years)
        context["profile"] = profile

        # Логика управления отображением сайдбара.
        layout_mode = self._resolve_layout_mode()
        context["layout_mode"] = layout_mode
        context["show_sidebar"] = layout_mode == "sidebar"
        if layout_mode != "sidebar":
            context["menu_variant"] = "without-sidebar"

        context["title_psychologist_catalog_detail_page_view"] = (
            f"{profile.user.first_name} {profile.user.last_name} — профиль психолога"
        )
        context["catalog_back_url"] = self._build_catalog_back_url(layout_mode)

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "psychologist-catalog"

        return context
