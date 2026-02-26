from urllib.parse import urlencode


class SpecialistMatchingLayoutMixin:
    """Единый mixin для сохранения режима отображения layout в цепочке подбора психолога.
    Что решает:
        1) Пользователь может открыть шаг подбора либо из верхнего меню, либо из сайдбара.
        2) Этот выбор должен сохраняться на всех шагах (1 -> 2 -> 3 -> 4), включая POST -> redirect.
        3) Даже если на очередном шаге query-параметр layout не передали, берем последнее значение из session."""

    # Ключ в session, в котором храним текущий режим layout для всей цепочки подбора
    LAYOUT_SESSION_KEY = "specialist_matching_layout_mode"
    VALID_LAYOUTS = {"menu", "sidebar"}
    DEFAULT_LAYOUT = "menu"

    def _resolve_layout_mode(self):
        """Определяет текущий layout (sidebar/menu) и кеширует его в рамках одного request.
        Приоритет источников:
            1) request.GET["layout"] - прямой переход по ссылке.
            2) request.POST["layout"] - submit формы текущего шага.
            3) session[LAYOUT_SESSION_KEY] - значение, сохраненное на предыдущих шагах.
            4) DEFAULT_LAYOUT ("menu") - безопасный дефолт."""
        if hasattr(self, "_layout_mode_cache"):
            return self._layout_mode_cache

        layout_from_request = self.request.GET.get("layout") or self.request.POST.get("layout")

        # Для первого шага ("general-questions") без явного layout всегда берем menu.
        # Это защищает от ситуации, когда пользователь просто открыл URL руками, а в session остался
        # старый режим (например, sidebar с прошлой сессии работы)
        if (not layout_from_request and self.request.resolver_match
                and self.request.resolver_match.url_name == "general-questions"):
            layout = self.DEFAULT_LAYOUT
        else:
            layout = (
                layout_from_request
                or self.request.session.get(self.LAYOUT_SESSION_KEY)
                or self.DEFAULT_LAYOUT
            )
        layout = str(layout).strip().lower()
        if layout not in self.VALID_LAYOUTS:
            layout = self.DEFAULT_LAYOUT

        # Сохраняем в session, чтобы следующий шаг мог восстановить режим даже без query
        self.request.session[self.LAYOUT_SESSION_KEY] = layout
        self._layout_mode_cache = layout
        return layout

    def _build_layout_query(self, **extra_params):
        """Собирает query-строку с обязательным layout и опциональными параметрами.
        Пример:
            _build_layout_query(reset=1) -> '?layout=sidebar&reset=1' """
        params = {"layout": self._resolve_layout_mode()}
        for key, value in extra_params.items():
            if value is None:
                continue
            params[key] = value
        return f"?{urlencode(params)}"

    def _apply_layout_context(self, context):
        """Добавляет в context все необходимое для корректного рендера меню/сайдбара.
        В шаблонах используем:
            - layout_mode: текущее значение ("menu" или "sidebar") для hidden input в формах.
            - layout_query: готовый query вида "?layout=sidebar" для ссылок между шагами.
            - show_sidebar/menu_variant: переключатель отображения шапки в base/menu шаблонах."""
        layout_mode = self._resolve_layout_mode()
        context["layout_mode"] = layout_mode
        context["layout_query"] = self._build_layout_query()
        context["show_sidebar"] = layout_mode == "sidebar"
        if layout_mode != "sidebar":
            context["menu_variant"] = "without-sidebar"
        return context
