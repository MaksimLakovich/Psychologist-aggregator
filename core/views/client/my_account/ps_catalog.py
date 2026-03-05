import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from aggregator._web.services.basic_filter_catalog import \
    CONSULTATION_TYPE_CHOICES
from core.services.experience_label import build_experience_label
from core.services.mixins_ps_catalog import (CatalogBackLinkMixin,
                                             CatalogLayoutModeMixin,
                                             CatalogPageDataMixin)
from core.services.topic_groups import (build_topics_grouped_by_type,
                                        serialize_topics_grouped_by_type)
from users.constants import GENDER_CHOICES
from users.models import Education, Method, PsychologistProfile


@method_decorator(ratelimit(key="user_or_ip", rate="60/m", block=True), name="post")
class PsychologistCatalogFilterAjaxView(LoginRequiredMixin, CatalogLayoutModeMixin, CatalogPageDataMixin, View):
    """AJAX endpoint для временной фильтрации каталога.

    Используемые миксины:
        - CatalogLayoutModeMixin: для безопасного fallback по layout_mode (чтобы понять, как рендерить
          страницу - с sidebar или с menu;
        - CatalogPageDataMixin: чтобы собрать краткие карточки каталога, пагинацию и JSON-ответ.

    Основная логика:
        - принимает текущие фильтры каталога в JSON;
        - возвращает уже отфильтрованные карточки и метаданные пагинации;
        - ничего не сохраняет в БД и не меняет ClientProfile.
    """

    http_method_names = ["post"]

    def _read_payload(self):
        """Читает JSON-body запроса и возвращает словарь.
        Если body пустой или битый, возвращаем пустой dict, чтобы дальше сработали безопасные fallback-значения."""
        try:
            raw_body = self.request.body.decode("utf-8") if self.request.body else "{}"
            payload = json.loads(raw_body or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}

        return payload if isinstance(payload, dict) else {}

    def post(self, request, *args, **kwargs):
        """Применяет фильтры каталога и возвращает JSON с карточками.
        Поддерживаемые поля payload (загрузки):
            - filters: текущие фильтры каталога;
            - page: какую страницу нужно получить;
            - order_key: существующий random order key или null;
            - restore_mode: нужно ли вернуть все карточки до текущей страницы;
            - layout_mode: sidebar/menu для корректных ссылок внутри карточек;
            - preview_only: если true, возвращаем только количество найденных специалистов.

        На текущем шаге filters может содержать:
            - consultation_type;
            - topic_ids;
            - method_ids;
            - gender;
            - price_individual_values;
            - price_couple_values;
            - age_min;
            - age_max.
            - experience_min;
            - experience_max.
            - session_time_mode;
            - selected_session_slots.
        """
        payload = self._read_payload()

        filters_state = self._extract_filters_state(payload.get("filters"))
        requested_page = self._parse_positive_int(payload.get("page"), fallback=1)
        random_order_key = self._parse_non_negative_int(payload.get("order_key"), fallback=None)
        restore_mode = bool(payload.get("restore_mode"))
        preview_only = bool(payload.get("preview_only"))
        layout_mode = payload.get("layout_mode")

        if layout_mode not in {"sidebar", "menu"}:
            layout_mode = self._resolve_layout_mode()

        if preview_only:
            return JsonResponse(
                self._build_preview_response_payload(filters_state=filters_state),
                status=200,
            )

        page_data = self._build_catalog_page_data(
            filters_state=filters_state,
            requested_page=requested_page,
            random_order_key=random_order_key,
            restore_mode=restore_mode,
        )

        return JsonResponse(
            self._build_ajax_response_payload(
                page_data=page_data,
                filters_state=filters_state,
                layout_mode=layout_mode,
            ),
            status=200,
        )


@method_decorator(ratelimit(key="user_or_ip", rate="60/m", block=True), name="get")
class PsychologistCatalogPageView(LoginRequiredMixin, CatalogLayoutModeMixin, CatalogPageDataMixin, TemplateView):
    """Контроллер на основе TemplateView для отображения страницы *Каталог психологов*.

    Используемые миксины:
        - CatalogLayoutModeMixin: чтобы понять, как рендерить страницу - с sidebar или с menu;
        - CatalogPageDataMixin: чтобы собрать краткие карточки каталога, пагинацию и корректные ссылки
          на детальную карточку (detail).

    Основная логика:
        - первый GET рендерит каталог карточек психологов (только верифицированные и активные);
        - первый запрос рендерит каталог без активных фильтров, показывает первые N-карточек и поддерживает
          кнопку "Показать еще" с догрузкой;
        - используется архитектура без Django-формы (чистый GET-поток);
        - первый запрос формирует случайный порядок карточек и закрепляет этот порядок в рамках текущей сессии
          через "ключ случайного порядка", чтобы при пагинации не было дублей и "прыгающего" списка;
        - дальнейшая фильтрация и восстановление состояния идут через AJAX, поэтому в HTML-странице не держим
          фильтры в query-параметрах.
    """

    template_name = "core/client_pages/my_account/psychologist_catalog.html"

    def get_context_data(self, **kwargs):
        """Формирование контекста для HTML-шаблона каталога (первый входа в каталог).
        - Первый вход всегда показывает "весь каталог" без фильтрации.
        - Возврат фильтров после detail-страницы делает frontend через sessionStorage + AJAX restore.

        В контекст передаем:
            - title_psychologist_catalog_page_view: SEO-title страницы каталога;
            - layout_mode: текущий режим отображения ("sidebar" или "menu");
            - show_sidebar: нужно ли показывать левую навигацию;
            - menu_variant: дополнительный флаг для шаблона base/menu, если страница открыта без sidebar;
            - catalog_detail_query: короткая query-строка для перехода из каталога в detail с сохранением layout;
            - consultation_type_choices: справочник вариантов фильтра "Вид консультации";
            - catalog_topics_by_type: JSON-совместимый словарь со сгруппированными темами для фильтра "Симптомы";
            - catalog_methods: JSON-совместимый список методов для фильтра "Подход";
            - catalog_gender_choices: JSON-совместимый справочник вариантов фильтра "Пол";
            - catalog_price_choices: JSON-совместимый словарь цен для фильтра "Цена";
            - catalog_age_bounds: реальные возрастные границы каталога для фильтра "Возраст";
            - catalog_experience_bounds: реальные границы стажа каталога для фильтра "Опыт";
            - catalog_domain_slots_endpoint: URL read-only эндпоинта доменных слотов для фильтра "Время сессии";
            - catalog_filter_endpoint: URL AJAX-endpoint для временной фильтрации каталога;
            - current_sidebar_key: ключ для серверной подсветки активного пункта боковой навигации;
            - profiles: карточки психологов для текущей страницы каталога;
            - has_next / next_page_number: состояние пагинации для кнопки "Показать еще";
            - current_page_number / total_pages / total_count: метаданные текущей выдачи каталога;
            - random_order_key: ключ стабильного случайного порядка карточек для догрузки и restore-сценария.
        """
        context = super().get_context_data(**kwargs)

        context["title_psychologist_catalog_page_view"] = "Каталог психологов на Опора — запись на приём к психологу"
        # Логика управления отображением сайдбара.
        # Используем единый layout_mode, чтобы одинаково работать для page=1 и page=2 и т.д.
        layout_mode = self._resolve_layout_mode()
        context["layout_mode"] = layout_mode
        context["show_sidebar"] = layout_mode == "sidebar"
        context["catalog_detail_query"] = self._build_catalog_detail_query(layout_mode)

        if layout_mode != "sidebar":
            context["menu_variant"] = "without-sidebar"

        context["consultation_type_choices"] = CONSULTATION_TYPE_CHOICES
        context["catalog_topics_by_type"] = serialize_topics_grouped_by_type(build_topics_grouped_by_type())
        context["catalog_methods"] = [
            {
                "id": str(method.pk),
                "name": method.name,
            }
            for method in Method.objects.all().order_by("name")
        ]
        context["catalog_gender_choices"] = {
            value: "Мужчина" if value == "male" else "Женщина" if value == "female" else label.title()
            for value, label in GENDER_CHOICES
        }
        context["catalog_price_choices"] = self._build_catalog_price_choices()
        context["catalog_age_bounds"] = self._build_catalog_age_bounds()
        context["catalog_experience_bounds"] = self._build_catalog_experience_bounds()
        context["catalog_domain_slots_endpoint"] = reverse("users:api:get-domain-slots")
        context["catalog_filter_endpoint"] = reverse("core:psychologist-catalog-filter")

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "psychologist-catalog"

        # ВАЖНО: обязательно добавляем page_data в context.
        # Иначе шаблон не получит profiles/has_next/total_count и карточки не отобразятся
        page_data = self._build_catalog_page_data(
            filters_state={
                "consultation_type": None,
                "topic_ids": [],
                "method_ids": [],
                "gender": None,
                "price_individual_values": [],
                "price_couple_values": [],
                "age_min": None,
                "age_max": None,
                "experience_min": None,
                "experience_max": None,
                "session_time_mode": "any",
                "selected_session_slots": [],
            },
            requested_page=1,
            random_order_key=self._generate_random_order_key(),
            restore_mode=False,
        )
        context.update(page_data)

        return context


class PsychologistCardDetailPageView(LoginRequiredMixin, CatalogLayoutModeMixin, CatalogBackLinkMixin, TemplateView):
    """Контроллер на основе TemplateView для отображения страницы детального профиля психолога из каталога.
    Страница нужна для перехода из краткой карточки по кнопке "Смотреть профиль" на отдельный URL вида:
        - psychologist_catalog/anna-ivanova/

    Используемые миксины:
        - CatalogLayoutModeMixin: чтобы детальная карточка открывалась в том же layout-режиме как был
          открыт изначально каталог (с sidebar или с menu);
        - CatalogBackLinkMixin: чтобы собрать короткий server fallback для кнопки "Назад в каталог".
    """

    template_name = "core/client_pages/my_account/psychologist_card_detail.html"

    def get_context_data(self, **kwargs):
        """Формирование контекста для HTML-шаблона детальной страницы психолога.
        В контекст передаем:
            - title_psychologist_catalog_detail_page_view: title детальной страницы психолога;
            - profile: объект PsychologistProfile с уже подготовленным profile.experience_label для UI;
            - layout_mode: текущий режим отображения ("sidebar" или "menu");
            - show_sidebar: нужно ли показывать левую навигацию;
            - menu_variant: дополнительный флаг для шаблона base/menu, если страница открыта без sidebar;
            - catalog_back_url: короткий server fallback URL для кнопки "Назад в каталог";
            - current_sidebar_key: ключ для серверной подсветки активного пункта боковой навигации.
        """
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

        context["title_psychologist_catalog_detail_page_view"] = (
            f"{profile.user.first_name} {profile.user.last_name} — профиль психолога"
        )

        profile.experience_label = build_experience_label(profile.work_experience_years)
        context["profile"] = profile

        # Готовим JSON-контракт одного психолога для JS-рендера detail-карточки.
        # Это дает 100% переиспользование карточного runtime, как на странице подбора.
        educations = Education.objects.filter(creator=profile.user).order_by("-year_start")
        context["detail_profile_payload"] = {
            "id": profile.id,
            "full_name": f"{profile.user.first_name} {profile.user.last_name}".strip(),
            "photo": profile.photo.url if profile.photo else "/static/images/menu/user-circle.svg",
            "rating": str(profile.rating),
            "experience_label": profile.experience_label,
            "biography": profile.biography or "",
            "methods": [
                {
                    "id": method.id,
                    "name": method.name,
                    "description": method.description,
                }
                for method in profile.methods.all()
            ],
            "topics": [
                {
                    "id": topic.id,
                    "name": topic.name,
                }
                for topic in profile.topics.all()
            ],
            "educations": [
                {
                    "year_start": edu.year_start,
                    "year_end": edu.year_end,
                    "institution": edu.institution,
                    "specialisation": edu.specialisation,
                }
                for edu in educations
            ],
            "price_individual": str(profile.price_individual),
            "price_couples": str(profile.price_couples),
            "price_currency": profile.price_currency,
        }

        # Логика управления отображением сайдбара
        layout_mode = self._resolve_layout_mode()
        context["layout_mode"] = layout_mode
        context["show_sidebar"] = layout_mode == "sidebar"
        if layout_mode != "sidebar":
            context["menu_variant"] = "without-sidebar"

        context["catalog_back_url"] = self._build_catalog_back_url(layout_mode)

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "psychologist-catalog"

        return context
