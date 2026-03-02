import random
from urllib.parse import urlencode
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Case, IntegerField, Value, When
from django.template.loader import render_to_string
from django.urls import reverse
from aggregator._web.services.basic_filter_catalog import apply_catalog_basic_filters, extract_consultation_type, extract_topic_ids
from core.constants import CARDS_PER_PAGE
from core.services.experience_label import build_experience_label
from users.models import PsychologistProfile
from users.services.slug import generate_unique_slug


class CatalogLayoutModeMixin:
    """Определяет layout-режим (sidebar или menu) каталога и детальной карточки.

    Этот mixin нужен только для одной задачи:
        - понять, как сейчас должен отображаться интерфейс: через sidebar или через menu.
    """

    CATALOG_LAYOUT_MODE_SESSION_KEY = "psychologist_catalog_layout_mode"

    def _resolve_layout_mode(self):
        """Определяет текущий layout каталога: sidebar или menu.

        Возвращает:
            - "sidebar" -> нужно показывать левую навигацию;
            - "menu" -> страница рендерится без левого сайдбара.

        Для обычного GET-входа логика такая:
            1) если layout явно пришел в query, используем его;
            2) если layout не пришел, то берем "menu".

        Для AJAX-сценариев используем session fallback,
        если фронтенд по какой-то причине не передал layout_mode.

        Почему так:
            - свежий вход в каталог не должен случайно тянуть старый layout из давней session;
            - но технический POST-запрос все равно должен иметь безопасный запасной вариант.
        """
        # 1) Ветка для GET-запроса, где используется query
        layout_from_query = self.request.GET.get("layout")

        if layout_from_query in {"sidebar", "menu"}:
            self.request.session[self.CATALOG_LAYOUT_MODE_SESSION_KEY] = layout_from_query
            return layout_from_query

        if self.request.method == "GET":
            self.request.session[self.CATALOG_LAYOUT_MODE_SESSION_KEY] = "menu"
            return "menu"

        # 2) Ветка "безопасный запасной вариант" для других типов запросов (например, POST), где используется session
        layout_from_session = self.request.session.get(self.CATALOG_LAYOUT_MODE_SESSION_KEY)

        if layout_from_session in {"sidebar", "menu"}:
            return layout_from_session  # Пытаемся достать из сессии

        self.request.session[self.CATALOG_LAYOUT_MODE_SESSION_KEY] = "menu"
        return "menu"  # Если в сессии пусто, ставим дефолт


class CatalogPsychologistQuerysetMixin:
    """Отвечает только за базовый QuerySet каталога психологов."""

    def get_queryset(self):
        """Возвращает базовый QuerySet для каталога психологов.

        Основная бизнес-логика:
            1) берем только активных и верифицированных специалистов;
            2) сразу подтягиваем связанные данные через select_related/prefetch_related, чтобы избежать N+1;
            3) базовую сортировку оставляем стабильной по id, а реальную случайность применяем безопасно
               на уровне списка id (random.shuffle() + ключ случайного порядка).

        "Случайность" - это рандомный вывод ВСЕХ карточек БЕЗ фильтрации при первом открытии страницы, чтоб
        была динамика. Далее мы добавим коэффициент совпадения при наличии фильтрации и ранжированный вывод.
        """
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

        У нас в модели есть автозаполнение, но лучше добавить защитный слой
        на переходный период, если у старых записей slug еще не был заполнен.
        Основная логика:
            1) После добавления нового поля slug в модель у части старых записей может быть NULL
                до выполнения миграции/бэкфилла.
            2) Каталог и карточки должны стабильно работать даже в этот переходный период.
        """
        if profile.slug:
            return

        full_name = f"{profile.user.first_name} {profile.user.last_name}".strip()
        source_value = full_name or profile.user.uuid
        profile.slug = generate_unique_slug(profile, source_value)
        profile.save(update_fields=["slug"])


class CatalogDetailLinkMixin:
    """Собирает короткие ссылки между каталогом и детальной карточкой (detail)."""

    @staticmethod
    def _build_catalog_detail_query(layout_mode):
        """Собирает query-строку для перехода из каталога в detail.

        - Передаем только layout.
        - Фильтры, текущая страница, anchor и random order key живут во frontend-state, а не в URL detail-страницы.
        """
        return f"?{urlencode({'layout': layout_mode})}"


class CatalogBackLinkMixin:
    """Собирает короткий server fallback для кнопки "Назад в каталог"."""

    @staticmethod
    def _build_catalog_back_url(layout_mode):
        """Собирает базовую ссылку "Назад в каталог" для non-JS fallback.

        - Передаем только layout.
        - Фильтры, текущую страницу и anchor фронтенд восстановит сам,
        если пользователь действительно возвращается из detail в каталог.
        """
        return f"{reverse('core:psychologist-catalog')}?{urlencode({'layout': layout_mode})}"


class CatalogPageDataMixin(CatalogPsychologistQuerysetMixin, CatalogDetailLinkMixin):
    """Собирает карточки каталога, пагинацию и AJAX payload.

    Этот mixin нужен для страниц, которые реально работают со списком карточек:
        - полной странице каталога;
        - AJAX endpoint для фильтрации и догрузки.
    """

    page_size = CARDS_PER_PAGE

    @staticmethod
    def _parse_positive_int(raw_value, fallback=1):
        """Преобразует входное значение в целое число больше нуля.

        Примеры:
            - "3" -> 3
            - 7 -> 7
            - "abc" -> fallback
            - 0 -> fallback
        """
        try:
            parsed_value = int(raw_value)
        except (TypeError, ValueError):
            return fallback

        if parsed_value > 0:
            return parsed_value
        return fallback

    @staticmethod
    def _parse_non_negative_int(raw_value, fallback=None):
        """Преобразует входное значение в целое число >= 0.

        Это нужно для random order key, потому что ключ может быть равен 0.
        """
        try:
            parsed_value = int(raw_value)
        except (TypeError, ValueError):
            return fallback

        if parsed_value >= 0:
            return parsed_value
        return fallback

    @staticmethod
    def _generate_random_order_key():
        """Создает новый ключ случайного порядка карточек.

        Пояснение:
            - это число, по которому мы детерминированно перемешиваем id психологов;
            - пока ключ один и тот же, порядок карточек тоже один и тот же;
            - если ключ новый, каталог получает новый случайный порядок и карточки будут в новом порядке.
        """
        return random.randrange(10**9)

    @staticmethod
    def _extract_filters_state(raw_filters_state=None):
        """Собирает текущее состояние фильтров каталога в едином формате.

        Для чего делаем это отдельным шагом:
            - фронтенд может прислать пустой объект, часть полей или битые значения;
            - на выходе backend всегда получает предсказуемую структуру.

        На текущем шаге формат такой:
            {
                "consultation_type": "individual" | "couple" | None,
                "topic_ids": ["1", "2"] | [],
            }
        """
        raw_filters_state = raw_filters_state or {}

        return {
            "consultation_type": extract_consultation_type(
                raw_filters_state.get("consultation_type")
            ),
            "topic_ids": extract_topic_ids(
                raw_filters_state.get("topic_ids")
            ),
        }

    def _build_catalog_page_data(self, *, filters_state, requested_page=1, random_order_key=None, restore_mode=False):
        """Собирает данные каталога для полной страницы (page=1 / page=2 / ...) или AJAX-ответа (фильтрация).

        Аргументы:
            - filters_state: словарь активных фильтров;
            - requested_page: номер страницы, которую нужно получить;
            - random_order_key: ключ стабильного случайного порядка;
            - restore_mode: если True и страница > 1, возвращаем карточки с 1-й страницы и до requested_page
              включительно. Это нужно для возврата из детальной карточки (detail) обратно в каталог,
              чтобы клиент увидел тот же набор карточек в каталоге, что и до перехода.

        Техническая логика (простыми словами):
            1) берем id всех подходящих психологов из БД;
            2) перемешиваем эти id по "ключу случайного порядка";
            3) берем только нужный кусок страницы (например, 1-18 или 19-36);
            4) вторым запросом в БД забираем данные только по этим id.
        """
        queryset = apply_catalog_basic_filters(
            self.get_queryset(),
            self._extract_filters_state(filters_state),
        )

        safe_random_order_key = self._parse_non_negative_int(
            random_order_key,
            fallback=self._generate_random_order_key(),
        )

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
                "random_order_key": safe_random_order_key,
            }

        # 2) Перемешиваем детерминированно через "ключ случайного порядка"
        rng = random.Random(safe_random_order_key)
        rng.shuffle(profile_ids)

        # 3) Пагинируем уже перемешанный список id
        paginator = Paginator(profile_ids, self.page_size)
        safe_requested_page = self._parse_positive_int(requested_page, fallback=1)

        try:
            page_obj = paginator.page(safe_requested_page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        # Для сценария "возврат из детальной карточки в каталог":
        # если указан restore=1 и page>1, то нужно вернуть НЕ только page=2,
        # а всю ленту от начала и до конца этой страницы (1..2, 1..3 и т.д.),
        # чтобы пользователь визуально оказался в том же месте списка
        if restore_mode and page_obj.number > 1:
            current_page_ids = profile_ids[:page_obj.end_index()]
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
            "random_order_key": safe_random_order_key,
        }

    def _render_cards_html(self, *, page_data, layout_mode):
        """Рендерит HTML карточек для AJAX-ответа.

        Здесь используем тот же partial-шаблон, что и у полной страницы,
        чтобы не расходилась верстка между SSR и AJAX.
        """
        return render_to_string(
            "core/client_pages/my_account/short_cards.html",
            {
                "profiles": page_data["profiles"],
                "layout_mode": layout_mode,
                "catalog_detail_query": self._build_catalog_detail_query(layout_mode),
                "show_sidebar": layout_mode == "sidebar",
            },
            request=self.request,
        )

    def _build_ajax_response_payload(self, *, page_data, filters_state, layout_mode):
        """Собирает единый JSON-ответ для фронтенда каталога.

        Этот ответ специально сделан "толстым", чтобы фронтенд после одного запроса мог сразу обновить:
            - карточки;
            - кнопку "Показать еще";
            - индикатор страницы;
            - пустое состояние каталога;
            - активность фильтр-чипов.
        """
        return {
            "status": "ok",
            "cards_html": self._render_cards_html(page_data=page_data, layout_mode=layout_mode),
            "has_next": page_data["has_next"],
            "next_page_number": page_data["next_page_number"],
            "current_page_number": page_data["current_page_number"],
            "total_pages": page_data["total_pages"],
            "total_count": page_data["total_count"],
            "random_order_key": page_data["random_order_key"],
            "active_filters": self._extract_filters_state(filters_state),
        }

    def _build_preview_response_payload(self, *, filters_state):
        """Собирает облегченный JSON-ответ только с количеством результатов.

        Этот режим нужен для модалок фильтров, когда пользователь еще не применил изменения,
        но уже хочет увидеть, сколько специалистов будет найдено.
        """
        filtered_queryset = apply_catalog_basic_filters(
            self.get_queryset(),
            self._extract_filters_state(filters_state),
        )

        return {
            "status": "ok",
            "total_count": filtered_queryset.count(),
            "active_filters": self._extract_filters_state(filters_state),
        }
