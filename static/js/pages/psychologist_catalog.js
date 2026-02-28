import {
    clearCatalogState,
    consumeCatalogRestorePending,
    readCatalogState,
    toNonNegativeInt,
    toPositiveInt,
    writeCatalogState,
} from "../modules/catalog_state.js";
import { initMultiToggle } from "../modules/toggle_group_multi_choice.js";
import { pluralizeRu } from "../utils/pluralize_ru.js";

/**
 * Логика страницы "Каталог психологов".
 *
 * В новой архитектуре этот файл отвечает за 5 задач:
 * 1) вкладки внутри карточек;
 * 2) AJAX-догрузку карточек по кнопке "Показать еще";
 * 3) временное хранение состояния каталога только для сценария catalog <-> detail;
 * 4) AJAX-применение фильтров без query-параметров в URL;
 * 5) восстановление каталога после возврата из detail.
 *
 * Важный принцип:
 * - каталог ничего не сохраняет в БД;
 * - фильтры живут только во frontend-state и sessionStorage текущей вкладки.
 */

const APPLY_RESULTS_LABEL = "Показать результаты";

/**
 * Здесь держим текущее рабочее состояние каталога.
 *
 * Почему нужен runtime-state рядом с DOM:
 * - DOM хранит только отображение;
 * - sessionStorage хранит резервную копию на возврат из detail;
 * - а runtime-state нужен для текущих AJAX-запросов и реактивного UI на странице.
 */
const catalogRuntimeState = {
    layout_mode: "menu",
    current_page: 1,
    total_pages: 0,
    order_key: null,
    anchor: null,
    scroll_y: 0,
    filters: {
        consultation_type: null,
    },
};

let cachedConsultationTypeChoices = null;
let cachedConsultationTypeCounts = null;

/**
 * Безопасно читает JSON из script-тега.
 */
function readJsonScript(id, fallback) {
    const scriptTag = document.getElementById(id);
    if (!scriptTag) return fallback;

    try {
        return JSON.parse(scriptTag.textContent || "null") ?? fallback;
    } catch (error) {
        return fallback;
    }
}

/**
 * Возвращает mapping вариантов вида консультации.
 *
 * Источник истины приходит с backend,
 * чтобы не дублировать справочник на frontend.
 */
function getConsultationTypeChoices() {
    if (cachedConsultationTypeChoices !== null) {
        return cachedConsultationTypeChoices;
    }

    const rawChoices = readJsonScript("catalog-consultation-type-choices-data", {});
    cachedConsultationTypeChoices = rawChoices && typeof rawChoices === "object" ? rawChoices : {};
    return cachedConsultationTypeChoices;
}

/**
 * Возвращает предрассчитанные количества карточек для фильтра "Вид консультации".
 */
function getConsultationTypeCounts() {
    if (cachedConsultationTypeCounts !== null) {
        return cachedConsultationTypeCounts;
    }

    const rawCounts = readJsonScript("catalog-consultation-type-counts-data", {});
    cachedConsultationTypeCounts = normalizeConsultationTypeCounts(rawCounts);
    return cachedConsultationTypeCounts;
}

/**
 * Приводит счетчики фильтра к безопасному виду.
 *
 * Пример результата:
 * {
 *   all: 40,
 *   individual: 39,
 *   couple: 4,
 * }
 */
function normalizeConsultationTypeCounts(rawCounts) {
    const parseCount = (value) => {
        const parsed = Number.parseInt(String(value), 10);
        return Number.isInteger(parsed) && parsed >= 0 ? parsed : 0;
    };

    return {
        all: parseCount(rawCounts?.all),
        individual: parseCount(rawCounts?.individual),
        couple: parseCount(rawCounts?.couple),
    };
}

/**
 * Нормализует входное значение фильтра "Вид консультации".
 *
 * Если значение невалидно, считаем, что фильтр не выбран.
 */
function normalizeConsultationType(rawValue) {
    if (typeof rawValue !== "string") return null;

    const choices = getConsultationTypeChoices();
    return Object.prototype.hasOwnProperty.call(choices, rawValue) ? rawValue : null;
}

/**
 * Собирает объект фильтров каталога в едином формате.
 *
 * Это задел под следующие фильтры:
 * сейчас внутри только consultation_type,
 * позже сюда аккуратно добавятся topics, methods, gender, age и так далее.
 */
function normalizeCatalogFilters(rawFilters = {}) {
    return {
        consultation_type: normalizeConsultationType(rawFilters?.consultation_type),
    };
}

/**
 * Возвращает кнопку "Показать еще".
 *
 * Вся техническая конфигурация каталога сейчас привязана к ней через data-атрибуты,
 * поэтому это удобная точка чтения текущих значений из DOM.
 */
function getLoadMoreButton() {
    return document.getElementById("catalog-load-more-btn");
}

/**
 * Возвращает endpoint AJAX-фильтрации каталога.
 */
function resolveCatalogFilterEndpoint() {
    const loadMoreButton = getLoadMoreButton();
    return loadMoreButton?.dataset.filterEndpoint || "";
}

/**
 * Возвращает выбранное значение в модалке "Вид консультации".
 *
 * Если активных кнопок нет, возвращаем null,
 * то есть режим "показать всех".
 */
function getModalSelectedConsultationType() {
    const hiddenInput = document.querySelector("#catalog-consultation-hidden-inputs input");
    return normalizeConsultationType(hiddenInput ? hiddenInput.value : null);
}

/**
 * Перерисовывает кнопку "Показать результаты" с количеством найденных специалистов.
 */
function renderApplyButtonWithCount(applyButton, selectedConsultationType) {
    if (!applyButton) return;

    const counts = getConsultationTypeCounts();
    const countKey = selectedConsultationType || "all";
    const selectedCount = counts[countKey] ?? counts.all ?? 0;
    const specialistWord = pluralizeRu(
        selectedCount,
        "специалист",
        "специалиста",
        "специалистов",
    );

    applyButton.innerHTML = `
        ${APPLY_RESULTS_LABEL}
        <span class="block mt-1 text-xs font-medium text-indigo-100">
            Найдено: ${selectedCount} ${specialistWord}
        </span>
    `;
}

/**
 * Обновляет внешний вид фильтр-чипа на странице каталога.
 *
 * Простая бизнес-логика:
 * - если фильтр выбран, кнопка получает индикатор активного состояния;
 * - если фильтр снят, кнопка возвращается к обычному виду.
 */
function renderFilterChipStates() {
    const consultationChip = document.querySelector('[data-filter-chip][data-filter-key="consultation_type"]');
    if (!consultationChip) return;

    const isActive = Boolean(catalogRuntimeState.filters.consultation_type);
    consultationChip.classList.toggle("bg-indigo-200/40", isActive);
    consultationChip.classList.toggle("text-indigo-700", isActive);
    consultationChip.classList.toggle("bg-slate-200/40", !isActive);
    consultationChip.classList.toggle("text-slate-600", !isActive);
}

/**
 * Обновляет текстовый индикатор текущей страницы внизу каталога.
 */
function renderCurrentPageIndicator(currentPage, totalPages) {
    const indicator = document.getElementById("catalog-page-indicator");
    if (!indicator) return;

    const safeTotalPages = toNonNegativeInt(totalPages, 0);
    if (safeTotalPages === 0) {
        indicator.textContent = "0 из 0";
        return;
    }

    const safeCurrentPage = toPositiveInt(currentPage, 1);
    indicator.textContent = `${Math.min(safeCurrentPage, safeTotalPages)} из ${safeTotalPages}`;
}

/**
 * Обновляет кнопку "Показать еще" после любого AJAX-ответа.
 *
 * Именно сервер сообщает, есть ли следующая страница и какой у нее номер,
 * поэтому источник истины здесь всегда backend response.
 */
function syncLoadMoreButton(data) {
    const loadMoreButton = getLoadMoreButton();
    if (!loadMoreButton) return;

    loadMoreButton.dataset.currentPage = String(toPositiveInt(data.current_page_number, 1));
    loadMoreButton.dataset.totalPages = String(toNonNegativeInt(data.total_pages, 0));

    const nextPageNumber = toPositiveInt(data.next_page_number, null);
    if (data.has_next && nextPageNumber) {
        loadMoreButton.dataset.nextPage = String(nextPageNumber);
        loadMoreButton.hidden = false;
    } else {
        loadMoreButton.dataset.nextPage = "";
        loadMoreButton.hidden = true;
    }

    const refreshedOrderKey = toNonNegativeInt(data.random_order_key, catalogRuntimeState.order_key);
    loadMoreButton.dataset.randomOrderKey = refreshedOrderKey === null ? "" : String(refreshedOrderKey);
    loadMoreButton.dataset.layout = catalogRuntimeState.layout_mode;
}

/**
 * Показывает или скрывает пустое состояние каталога.
 */
function renderEmptyState(totalCount) {
    const emptyState = document.getElementById("catalog-empty-state");
    if (!emptyState) return;

    emptyState.classList.toggle("hidden", toNonNegativeInt(totalCount, 0) > 0);
}

/**
 * Инициализирует вкладки внутри карточек.
 *
 * Важный момент:
 * - карточки появляются и при первом SSR-рендере, и после AJAX;
 * - поэтому инициализацию можно вызывать повторно,
 *   а каждая карточка сама защищается флагом tabsInitialized.
 */
function initCardTabs(scope = document) {
    const cards = scope.querySelectorAll("[data-catalog-card]");

    cards.forEach((card) => {
        const tabButtons = card.querySelectorAll("[data-tab-button]");
        const tabPanels = card.querySelectorAll("[data-tab-panel]");

        if (!tabButtons.length || !tabPanels.length) return;
        if (card.dataset.tabsInitialized === "1") return;

        const activateTab = (target) => {
            tabButtons.forEach((button) => {
                const isActive = button.dataset.target === target;
                button.setAttribute("aria-selected", String(isActive));
                button.classList.toggle("bg-indigo-100", isActive);
                button.classList.toggle("text-indigo-700", isActive);
                button.classList.toggle("bg-gray-100", !isActive);
                button.classList.toggle("text-gray-600", !isActive);
            });

            tabPanels.forEach((panel) => {
                panel.classList.toggle("hidden", panel.dataset.tabPanel !== target);
            });
        };

        tabButtons.forEach((button) => {
            button.addEventListener("click", () => activateTab(button.dataset.target));
        });

        activateTab("main");
        card.dataset.tabsInitialized = "1";
    });
}

/**
 * Считывает стартовое состояние каталога из серверного HTML.
 *
 * Это базовая точка, от которой потом отталкиваются фильтры, догрузка и restore.
 */
function hydrateRuntimeStateFromDom() {
    const loadMoreButton = getLoadMoreButton();
    if (!loadMoreButton) return;

    catalogRuntimeState.layout_mode = loadMoreButton.dataset.layout === "sidebar" ? "sidebar" : "menu";
    catalogRuntimeState.current_page = toPositiveInt(loadMoreButton.dataset.currentPage, 1);
    catalogRuntimeState.total_pages = toNonNegativeInt(loadMoreButton.dataset.totalPages, 0);
    catalogRuntimeState.order_key = toNonNegativeInt(loadMoreButton.dataset.randomOrderKey, null);
    catalogRuntimeState.filters = normalizeCatalogFilters({ consultation_type: null });
}

/**
 * Сохраняет текущее состояние каталога в sessionStorage.
 *
 * Это резервный снимок каталога на случай возврата из detail.
 */
function persistCatalogState(extraState = {}) {
    writeCatalogState({
        layout_mode: catalogRuntimeState.layout_mode,
        current_page: catalogRuntimeState.current_page,
        total_pages: catalogRuntimeState.total_pages,
        order_key: catalogRuntimeState.order_key,
        filters: normalizeCatalogFilters(catalogRuntimeState.filters),
        anchor: catalogRuntimeState.anchor,
        scroll_y: catalogRuntimeState.scroll_y,
        updated_at: Date.now(),
        ...extraState,
    });
}

/**
 * Возвращает заголовки для POST-запроса каталога.
 */
function buildCatalogRequestHeaders() {
    return {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": window.CSRF_TOKEN || "",
    };
}

/**
 * Выполняет AJAX-запрос к backend и возвращает JSON каталога.
 */
async function requestCatalogData({ page, orderKey = null, restoreMode = false }) {
    const endpoint = resolveCatalogFilterEndpoint();
    if (!endpoint) {
        throw new Error("catalog_filter_endpoint_missing");
    }

    const response = await fetch(endpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: buildCatalogRequestHeaders(),
        body: JSON.stringify({
            filters: normalizeCatalogFilters(catalogRuntimeState.filters),
            page,
            order_key: orderKey,
            restore_mode: restoreMode,
            layout_mode: catalogRuntimeState.layout_mode,
        }),
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    if (data.status !== "ok") {
        throw new Error("invalid_catalog_response");
    }

    return data;
}

/**
 * Применяет AJAX-ответ к интерфейсу каталога.
 *
 * replaceMode=false:
 * - полностью заменяем сетку карточек.
 *
 * appendMode=true:
 * - добавляем новые карточки вниз к уже показанным.
 */
function applyCatalogResponse(data, { appendMode = false } = {}) {
    const grid = document.getElementById("catalog-cards-grid");
    if (!grid) return;

    const temp = document.createElement("div");
    temp.innerHTML = data.cards_html || "";
    const incomingCards = Array.from(temp.querySelectorAll("[data-catalog-card]"));

    if (!appendMode) {
        grid.innerHTML = "";
    }

    incomingCards.forEach((card) => grid.appendChild(card));
    initCardTabs(grid);

    catalogRuntimeState.current_page = toPositiveInt(data.current_page_number, 1);
    catalogRuntimeState.total_pages = toNonNegativeInt(data.total_pages, 0);
    catalogRuntimeState.order_key = toNonNegativeInt(data.random_order_key, catalogRuntimeState.order_key);
    catalogRuntimeState.filters = normalizeCatalogFilters(data.active_filters || catalogRuntimeState.filters);

    if (data.consultation_type_counts && typeof data.consultation_type_counts === "object") {
        cachedConsultationTypeCounts = normalizeConsultationTypeCounts(data.consultation_type_counts);
    }

    syncLoadMoreButton(data);
    renderCurrentPageIndicator(catalogRuntimeState.current_page, catalogRuntimeState.total_pages);
    renderEmptyState(data.total_count);
    renderFilterChipStates();
    persistCatalogState();
}

/**
 * Восстанавливает позицию прокрутки после возврата из detail.
 *
 * Приоритет такой:
 * 1) если знаем конкретную карточку, прокручиваем к ней;
 * 2) если карточка не найдена, используем сохраненный scroll_y;
 * 3) если и его нет, просто остаемся наверху списка.
 */
function restoreCatalogScrollPosition(savedState) {
    if (!savedState) return;

    const anchor = typeof savedState.anchor === "string" ? savedState.anchor.trim() : "";
    if (anchor) {
        const anchorElement = document.getElementById(`psychologist-card-${anchor}`);
        if (anchorElement) {
            anchorElement.scrollIntoView({ block: "center", behavior: "auto" });
            return;
        }
    }

    const scrollY = toNonNegativeInt(savedState.scroll_y, null);
    if (scrollY !== null) {
        window.scrollTo({ top: scrollY, behavior: "auto" });
    }
}

/**
 * Применяет фильтр "Вид консультации" через AJAX.
 *
 * Что происходит по шагам:
 * 1) обновляем runtime-state;
 * 2) просим backend вернуть первую страницу уже с этим фильтром;
 * 3) полностью заменяем карточки и метаданные каталога;
 * 4) сохраняем обновленное состояние для возможного возврата из detail.
 */
async function applyConsultationTypeFilter(selectedValue) {
    const loadMoreButton = getLoadMoreButton();
    const errorLabel = document.getElementById("catalog-load-more-error");
    if (!loadMoreButton) return false;

    loadMoreButton.disabled = true;
    if (errorLabel) errorLabel.classList.add("hidden");

    const previousConsultationType = catalogRuntimeState.filters.consultation_type;
    const previousAnchor = catalogRuntimeState.anchor;
    const previousScrollY = catalogRuntimeState.scroll_y;

    catalogRuntimeState.filters.consultation_type = normalizeConsultationType(selectedValue);
    catalogRuntimeState.anchor = null;
    catalogRuntimeState.scroll_y = Math.max(window.scrollY, 0);

    try {
        const data = await requestCatalogData({
            page: 1,
            orderKey: null,
            restoreMode: false,
        });
        applyCatalogResponse(data, { appendMode: false });
        return true;
    } catch (error) {
        catalogRuntimeState.filters.consultation_type = previousConsultationType;
        catalogRuntimeState.anchor = previousAnchor;
        catalogRuntimeState.scroll_y = previousScrollY;
        console.error("Ошибка применения фильтра каталога:", error);
        if (errorLabel) errorLabel.classList.remove("hidden");
        return false;
    } finally {
        loadMoreButton.disabled = false;
    }
}

/**
 * Инициализирует модалку фильтров каталога.
 *
 * На этом шаге детально поддерживаем только фильтр "Вид консультации".
 * Остальные фильтры пока показывают заглушку, но сама архитектура уже общая.
 */
function initCatalogFiltersModal() {
    const modal = document.getElementById("filter-modal");
    const modalOverlay = document.getElementById("filter-modal-overlay");
    const modalTitle = document.getElementById("modal-title");
    const modalContent = document.getElementById("modal-content");
    const closeButton = document.getElementById("filter-modal-close-btn");
    const applyButton = document.getElementById("filter-modal-apply-btn");
    const filterButtons = document.querySelectorAll("[data-filter-chip]");

    if (
        !modal ||
        !modalOverlay ||
        !modalTitle ||
        !modalContent ||
        !closeButton ||
        !applyButton ||
        !filterButtons.length
    ) {
        return;
    }

    let openedFilterName = null;

    function closeModal() {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
        document.body.style.overflow = "";
    }

    function openModal(filterName) {
        openedFilterName = filterName;
        modalTitle.textContent = filterName;
        renderModalContent(filterName);
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        document.body.style.overflow = "hidden";
    }

    function renderModalContent(filterName) {
        if (filterName !== "Вид консультации") {
            modalContent.innerHTML = `
                <p class="text-sm text-gray-500 leading-relaxed">
                    Этот фильтр будет подключен на следующем шаге. Сейчас можно закрыть модалку.
                </p>
            `;
            applyButton.textContent = APPLY_RESULTS_LABEL;
            return;
        }

        const consultationTypeChoices = getConsultationTypeChoices();
        const individualLabel = consultationTypeChoices.individual || "Индивидуальная";
        const coupleLabel = consultationTypeChoices.couple || "Парная";
        const activeConsultationType = catalogRuntimeState.filters.consultation_type;

        modalContent.innerHTML = `
            <div class="space-y-4">
                <p class="text-sm text-gray-500 leading-relaxed">
                    Выберите формат консультации для фильтрации карточек
                </p>
                <div id="catalog-consultation-block" class="grid grid-cols-2 gap-3 max-w-md">
                    <button type="button" data-value="individual" class="catalog-consultation-btn px-4 py-2 rounded-lg border text-base font-medium">
                        ${individualLabel}
                    </button>
                    <button type="button" data-value="couple" class="catalog-consultation-btn px-4 py-2 rounded-lg border text-base font-medium">
                        ${coupleLabel}
                    </button>
                </div>
                <div id="catalog-consultation-hidden-inputs" class="hidden"></div>
                <p class="text-xs text-gray-400">
                    Можно оставить оба варианта невыбранными — это режим "все специалисты"
                </p>
            </div>
        `;

        // Для каталога нужен сценарий "выбрать 1 вариант или снять выбор совсем".
        // Именно поэтому используем уже существующий multi-toggle с maxSelected=1.
        initMultiToggle({
            containerSelector: "#catalog-consultation-block",
            buttonSelector: ".catalog-consultation-btn",
            hiddenInputsContainerSelector: "#catalog-consultation-hidden-inputs",
            inputName: "consultation_type",
            initialValues: activeConsultationType ? [activeConsultationType] : [],
            maxSelected: 1,
        });

        renderApplyButtonWithCount(applyButton, getModalSelectedConsultationType());

        const consultationBlock = document.getElementById("catalog-consultation-block");
        if (consultationBlock) {
            consultationBlock.addEventListener("click", (event) => {
                if (!event.target.closest(".catalog-consultation-btn")) return;

                // Даем toggle-модулю один animation frame,
                // чтобы он успел обновить hidden-input, и только потом читаем новое значение.
                window.requestAnimationFrame(() => {
                    renderApplyButtonWithCount(applyButton, getModalSelectedConsultationType());
                });
            });
        }
    }

    async function applyCurrentFilter() {
        if (openedFilterName !== "Вид консультации") {
            closeModal();
            return;
        }

        const isApplied = await applyConsultationTypeFilter(getModalSelectedConsultationType());
        if (isApplied) {
            closeModal();
        }
    }

    filterButtons.forEach((button) => {
        button.addEventListener("click", () => {
            openModal(button.dataset.filterName || "Фильтр");
        });
    });

    modalOverlay.addEventListener("click", closeModal);
    closeButton.addEventListener("click", closeModal);
    applyButton.addEventListener("click", applyCurrentFilter);

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !modal.classList.contains("hidden")) {
            closeModal();
        }
    });
}

/**
 * Инициализирует кнопку "Показать еще".
 *
 * Здесь уже нет GET-параметров partial/order_key/filter в URL.
 * Вместо этого фронтенд отправляет POST с текущим состоянием каталога.
 */
function initLoadMore() {
    const grid = document.getElementById("catalog-cards-grid");
    const loadMoreButton = getLoadMoreButton();
    const errorLabel = document.getElementById("catalog-load-more-error");

    if (!grid || !loadMoreButton) return;

    loadMoreButton.addEventListener("click", async () => {
        const requestedPage = toPositiveInt(loadMoreButton.dataset.nextPage, null);
        const orderKey = toNonNegativeInt(loadMoreButton.dataset.randomOrderKey, null);
        if (!requestedPage || orderKey === null) {
            loadMoreButton.hidden = true;
            return;
        }

        loadMoreButton.disabled = true;
        if (errorLabel) errorLabel.classList.add("hidden");

        try {
            const data = await requestCatalogData({
                page: requestedPage,
                orderKey,
                restoreMode: false,
            });
            applyCatalogResponse(data, { appendMode: true });
        } catch (error) {
            console.error("Ошибка догрузки карточек каталога:", error);
            if (errorLabel) errorLabel.classList.remove("hidden");
        } finally {
            loadMoreButton.disabled = false;
        }
    });
}

/**
 * Инициализирует кнопку "Вернуться в начало".
 */
function initScrollToTopButton() {
    const scrollTopButton = document.getElementById("catalog-scroll-top-btn");
    if (!scrollTopButton) return;

    scrollTopButton.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
}

/**
 * Включает сохранение состояния каталога перед переходом в detail.
 *
 * Что сохраняем:
 * - текущую страницу каталога;
 * - active filters;
 * - random order key;
 * - anchor карточки, по которой перешли;
 * - текущую прокрутку страницы.
 */
function initCatalogStatePersistence() {
    document.addEventListener("click", (event) => {
        const detailLink = event.target.closest("[data-catalog-detail-link]");
        if (!detailLink) return;

        catalogRuntimeState.anchor = detailLink.dataset.profileSlug || null;
        catalogRuntimeState.scroll_y = Math.max(window.scrollY, 0);
        persistCatalogState();
    });
}

/**
 * Пытается восстановить каталог после возврата из detail.
 *
 * Важное бизнес-правило:
 * - если пользователь открыл каталог заново, а не вернулся из detail,
 *   старое состояние удаляем и НЕ применяем.
 *
 * То есть restore работает только по одноразовому флагу,
 * который detail-страница ставит перед fallback-возвратом.
 */
async function restoreCatalogIfNeeded() {
    const shouldRestore = consumeCatalogRestorePending();
    const storedState = readCatalogState();

    if (!shouldRestore || !storedState) {
        clearCatalogState();
        persistCatalogState({
            anchor: null,
            scroll_y: Math.max(window.scrollY, 0),
        });
        return false;
    }

    catalogRuntimeState.layout_mode = storedState.layout_mode === "sidebar" ? "sidebar" : catalogRuntimeState.layout_mode;
    catalogRuntimeState.current_page = toPositiveInt(storedState.current_page, 1);
    catalogRuntimeState.order_key = toNonNegativeInt(storedState.order_key, null);
    catalogRuntimeState.anchor = typeof storedState.anchor === "string" ? storedState.anchor : null;
    catalogRuntimeState.scroll_y = toNonNegativeInt(storedState.scroll_y, 0);
    catalogRuntimeState.filters = normalizeCatalogFilters(storedState.filters || {});

    const loadMoreButton = getLoadMoreButton();
    const errorLabel = document.getElementById("catalog-load-more-error");
    if (loadMoreButton) {
        loadMoreButton.disabled = true;
    }
    if (errorLabel) {
        errorLabel.classList.add("hidden");
    }

    try {
        const data = await requestCatalogData({
            page: catalogRuntimeState.current_page,
            orderKey: catalogRuntimeState.order_key,
            restoreMode: true,
        });
        applyCatalogResponse(data, { appendMode: false });
        restoreCatalogScrollPosition(storedState);
        return true;
    } catch (error) {
        console.error("Ошибка восстановления каталога после detail:", error);
        clearCatalogState();
        persistCatalogState({
            anchor: null,
            scroll_y: Math.max(window.scrollY, 0),
        });
        if (errorLabel) {
            errorLabel.classList.remove("hidden");
        }
        return false;
    } finally {
        if (loadMoreButton) {
            loadMoreButton.disabled = false;
        }
    }
}

async function bootstrapCatalogPage() {
    hydrateRuntimeStateFromDom();
    renderCurrentPageIndicator(catalogRuntimeState.current_page, catalogRuntimeState.total_pages);
    renderFilterChipStates();

    initCatalogFiltersModal();
    initCardTabs();
    initLoadMore();
    initScrollToTopButton();

    await restoreCatalogIfNeeded();
    initCatalogStatePersistence();
}

document.addEventListener("DOMContentLoaded", () => {
    bootstrapCatalogPage().catch((error) => {
        console.error("Ошибка инициализации каталога:", error);
    });
});
