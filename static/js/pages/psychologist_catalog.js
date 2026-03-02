import {
    clearCatalogState,
    consumeCatalogRestorePending,
    readCatalogState,
    toNonNegativeInt,
    toPositiveInt,
    writeCatalogState,
} from "../modules/catalog_state.js";
import { initCollapsibleTopicGroups } from "../modules/collapsible_topics_list.js";
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
const PREVIEW_RESULTS_LABEL = "Считаем результаты...";

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
        topic_ids: [],
    },
};

let cachedConsultationTypeChoices = null;
let cachedTopicsByType = null;
let cachedTopicIdToTypeMap = null;
let activePreviewRequestId = 0;

function escapeHtml(value) {
    const sourceValue = String(value ?? "");

    return sourceValue
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\"", "&quot;")
        .replaceAll("'", "&#39;");
}

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

function getConsultationTypeChoices() {
    if (cachedConsultationTypeChoices !== null) {
        return cachedConsultationTypeChoices;
    }

    const rawChoices = readJsonScript("catalog-consultation-type-choices-data", {});
    cachedConsultationTypeChoices = rawChoices && typeof rawChoices === "object" ? rawChoices : {};
    return cachedConsultationTypeChoices;
}

function getCatalogTopicsByType() {
    if (cachedTopicsByType !== null) {
        return cachedTopicsByType;
    }

    const rawTopics = readJsonScript("catalog-topics-by-type-data", {});
    cachedTopicsByType = rawTopics && typeof rawTopics === "object" ? rawTopics : {};
    return cachedTopicsByType;
}

function getTopicIdToTypeMap() {
    if (cachedTopicIdToTypeMap !== null) {
        return cachedTopicIdToTypeMap;
    }

    const topicIdToTypeMap = {};
    const topicsByType = getCatalogTopicsByType();

    Object.entries(topicsByType).forEach(([topicTypeLabel, groups]) => {
        Object.values(groups || {}).forEach((topics) => {
            (topics || []).forEach((topic) => {
                if (!topic?.id) return;
                topicIdToTypeMap[String(topic.id)] = topicTypeLabel;
            });
        });
    });

    cachedTopicIdToTypeMap = topicIdToTypeMap;
    return cachedTopicIdToTypeMap;
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

function normalizeTopicIds(rawValues) {
    if (!Array.isArray(rawValues)) return [];

    const normalizedTopicIds = [];
    const seenTopicIds = new Set();

    rawValues.forEach((rawValue) => {
        const parsedValue = Number.parseInt(String(rawValue), 10);
        if (!Number.isInteger(parsedValue) || parsedValue <= 0) return;

        const normalizedValue = String(parsedValue);
        if (seenTopicIds.has(normalizedValue)) return;

        seenTopicIds.add(normalizedValue);
        normalizedTopicIds.push(normalizedValue);
    });

    return normalizedTopicIds;
}

function resolveTopicTypeLabel(consultationType) {
    if (!consultationType) return null;

    const choices = getConsultationTypeChoices();
    const rawLabel = choices[consultationType];
    return typeof rawLabel === "string" ? rawLabel : null;
}

function filterTopicIdsByConsultationType(topicIds, consultationType) {
    const normalizedTopicIds = normalizeTopicIds(topicIds);
    const topicTypeLabel = resolveTopicTypeLabel(consultationType);
    if (!topicTypeLabel) return normalizedTopicIds;

    const topicIdToTypeMap = getTopicIdToTypeMap();
    return normalizedTopicIds.filter((topicId) => topicIdToTypeMap[topicId] === topicTypeLabel);
}

function normalizeCatalogFilters(rawFilters = {}) {
    const consultationType = normalizeConsultationType(rawFilters?.consultation_type);
    const topicIds = filterTopicIdsByConsultationType(rawFilters?.topic_ids, consultationType);

    return {
        consultation_type: consultationType,
        topic_ids: topicIds,
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

function buildCatalogRequestHeaders() {
    return {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": window.CSRF_TOKEN || "",
    };
}

async function requestCatalogData({
    page = 1,
    orderKey = null,
    restoreMode = false,
    previewOnly = false,
    filtersOverride = null,
} = {}) {
    const endpoint = resolveCatalogFilterEndpoint();
    if (!endpoint) {
        throw new Error("catalog_filter_endpoint_missing");
    }

    const response = await fetch(endpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: buildCatalogRequestHeaders(),
        body: JSON.stringify({
            filters: normalizeCatalogFilters(filtersOverride || catalogRuntimeState.filters),
            page,
            order_key: orderKey,
            restore_mode: restoreMode,
            preview_only: previewOnly,
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
 * Перерисовывает кнопку "Показать результаты" с количеством найденных специалистов.
 */
function renderApplyButtonWithCount(applyButton, totalCount) {
    if (!applyButton) return;

    const safeCount = toNonNegativeInt(totalCount, 0);
    const specialistWord = pluralizeRu(
        safeCount,
        "терапевт",
        "терапевта",
        "терапевтов",
    );

    applyButton.innerHTML = `
        ${APPLY_RESULTS_LABEL}
        <span class="block mt-1 text-xs font-medium text-indigo-100">
            Найдено: ${safeCount} ${specialistWord}
        </span>
    `;
}

function renderApplyButtonLoading(applyButton) {
    if (!applyButton) return;

    applyButton.innerHTML = `
        ${APPLY_RESULTS_LABEL}
        <span class="block mt-1 text-xs font-medium text-indigo-100">
            ${PREVIEW_RESULTS_LABEL}
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
    const filterStates = {
        consultation_type: Boolean(catalogRuntimeState.filters.consultation_type),
        topic_ids: normalizeTopicIds(catalogRuntimeState.filters.topic_ids).length > 0,
    };

    Object.entries(filterStates).forEach(([filterKey, isActive]) => {
        const chip = document.querySelector(`[data-filter-chip][data-filter-key="${filterKey}"]`);
        if (!chip) return;

        chip.classList.toggle("bg-indigo-200/40", isActive);
        chip.classList.toggle("text-indigo-700", isActive);
        chip.classList.toggle("bg-slate-200/40", !isActive);
        chip.classList.toggle("text-slate-600", !isActive);
    });
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
    catalogRuntimeState.filters = normalizeCatalogFilters({
        consultation_type: null,
        topic_ids: [],
    });
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
async function applyCatalogFilters(partialFilters = {}) {
    const loadMoreButton = getLoadMoreButton();
    const errorLabel = document.getElementById("catalog-load-more-error");
    if (!loadMoreButton) return false;

    loadMoreButton.disabled = true;
    if (errorLabel) errorLabel.classList.add("hidden");

    const previousFilters = normalizeCatalogFilters(catalogRuntimeState.filters);
    const previousAnchor = catalogRuntimeState.anchor;
    const previousScrollY = catalogRuntimeState.scroll_y;

    catalogRuntimeState.filters = normalizeCatalogFilters({
        ...catalogRuntimeState.filters,
        ...partialFilters,
    });
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
        catalogRuntimeState.filters = previousFilters;
        catalogRuntimeState.anchor = previousAnchor;
        catalogRuntimeState.scroll_y = previousScrollY;
        console.error("Ошибка применения фильтра каталога:", error);
        if (errorLabel) errorLabel.classList.remove("hidden");
        return false;
    } finally {
        loadMoreButton.disabled = false;
    }
}

function getVisibleTopicTypeLabels() {
    const selectedConsultationType = catalogRuntimeState.filters.consultation_type;
    const selectedTopicTypeLabel = resolveTopicTypeLabel(selectedConsultationType);
    const topicsByType = getCatalogTopicsByType();

    if (selectedTopicTypeLabel && topicsByType[selectedTopicTypeLabel]) {
        return [selectedTopicTypeLabel];
    }

    return Object.keys(topicsByType);
}

function buildTopicsModalHtml(selectedTopicIds) {
    const topicsByType = getCatalogTopicsByType();
    const visibleTopicTypeLabels = getVisibleTopicTypeLabels();

    if (!visibleTopicTypeLabels.length) {
        return `
            <p class="text-sm text-gray-500 leading-relaxed">
                Темы пока не добавлены.
            </p>
        `;
    }

    const sectionsHtml = visibleTopicTypeLabels.map((topicTypeLabel) => {
        const groupedTopics = topicsByType[topicTypeLabel] || {};
        const groupsHtml = Object.entries(groupedTopics).map(([groupName, topics]) => {
            const itemsHtml = (topics || []).map((topic) => `
                <label class="topic-item flex items-center gap-3 p-1 rounded-md hover:bg-gray-50 transition">
                    <input
                        type="checkbox"
                        value="${topic.id}"
                        class="catalog-topic-checkbox w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                        ${selectedTopicIds.includes(String(topic.id)) ? "checked" : ""}
                    >
                    <span class="text-base font-medium text-gray-900">${escapeHtml(topic.name)}</span>
                </label>
            `).join("");

            return `
                <div class="topic-group mb-1 pb-4">
                    <p class="block mb-2 text-lg font-medium text-indigo-500">
                        <strong>${escapeHtml(groupName)}</strong>
                    </p>
                    <div class="topics-group grid grid-cols-1 sm:grid-cols-2">
                        ${itemsHtml || '<p class="text-base text-gray-500">Темы не найдены.</p>'}
                    </div>
                    <button
                        type="button"
                        class="show-more-topics hidden mt-2 italic text-sm font-medium text-indigo-500 hover:text-indigo-900"
                    >
                        Ещё
                    </button>
                </div>
            `;
        }).join("");

        const typeTitleHtml = visibleTopicTypeLabels.length > 1 ? `
            <div class="pt-2 pb-1 border-b border-slate-100">
                <p class="text-sm font-black uppercase tracking-[0.2em] text-slate-400">${escapeHtml(topicTypeLabel)}</p>
            </div>
        ` : "";

        return `
            <section class="space-y-3">
                ${typeTitleHtml}
                ${groupsHtml || '<p class="text-sm text-gray-500">Темы не найдены.</p>'}
            </section>
        `;
    }).join("");

    const helperText = catalogRuntimeState.filters.consultation_type
        ? "Показаны темы только для выбранного вида консультации."
        : "Можно выбрать темы как для индивидуальной, так и для парной консультации.";

    return `
        <div class="space-y-4">
            <p class="text-sm text-gray-500 leading-relaxed">
                Выберите симптомы и запросы, с которыми должен работать психолог.
            </p>
            <div id="catalog-topic-groups-root" class="max-h-[28rem] overflow-y-auto pr-1 space-y-5">
                ${sectionsHtml}
            </div>
            <p class="text-xs text-gray-400">
                ${helperText}
            </p>
        </div>
    `;
}

function getModalSelectedConsultationType() {
    const hiddenInput = document.querySelector("#catalog-consultation-hidden-inputs input");
    return normalizeConsultationType(hiddenInput ? hiddenInput.value : null);
}

function getModalSelectedTopicIds() {
    const checkboxes = document.querySelectorAll("#catalog-topic-groups-root .catalog-topic-checkbox:checked");
    return normalizeTopicIds(Array.from(checkboxes).map((checkbox) => checkbox.value));
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
    let previewDebounceTimer = null;

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

    function buildTentativeFiltersForModal() {
        if (openedFilterName === "Вид консультации") {
            return normalizeCatalogFilters({
                ...catalogRuntimeState.filters,
                consultation_type: getModalSelectedConsultationType(),
                topic_ids: catalogRuntimeState.filters.topic_ids,
            });
        }

        if (openedFilterName === "Симптомы") {
            return normalizeCatalogFilters({
                ...catalogRuntimeState.filters,
                topic_ids: getModalSelectedTopicIds(),
            });
        }

        return normalizeCatalogFilters(catalogRuntimeState.filters);
    }

    async function refreshApplyButtonPreview() {
        const requestId = ++activePreviewRequestId;
        renderApplyButtonLoading(applyButton);

        try {
            const previewData = await requestCatalogData({
                previewOnly: true,
                filtersOverride: buildTentativeFiltersForModal(),
            });

            if (requestId !== activePreviewRequestId) return;
            renderApplyButtonWithCount(applyButton, previewData.total_count);
        } catch (error) {
            if (requestId !== activePreviewRequestId) return;
            console.error("Ошибка preview-count каталога:", error);
            applyButton.textContent = APPLY_RESULTS_LABEL;
        }
    }

    function scheduleApplyButtonPreviewRefresh() {
        if (previewDebounceTimer) {
            window.clearTimeout(previewDebounceTimer);
        }

        previewDebounceTimer = window.setTimeout(() => {
            refreshApplyButtonPreview();
        }, 180);
    }

    function renderModalContent(filterName) {
        if (filterName === "Вид консультации") {
            const consultationTypeChoices = getConsultationTypeChoices();
            const individualLabel = consultationTypeChoices.individual || "Индивидуальная";
            const coupleLabel = consultationTypeChoices.couple || "Парная";
            const activeConsultationType = catalogRuntimeState.filters.consultation_type;

            modalContent.innerHTML = `
                <div class="space-y-4">
                    <p class="text-sm text-gray-500 leading-relaxed">
                        Выберите формат консультации для фильтрации карточек.
                    </p>
                    <div id="catalog-consultation-block" class="grid grid-cols-2 gap-3 max-w-md">
                        <button type="button" data-value="individual" class="catalog-consultation-btn px-4 py-2 rounded-lg border text-base font-medium">
                            ${escapeHtml(individualLabel)}
                        </button>
                        <button type="button" data-value="couple" class="catalog-consultation-btn px-4 py-2 rounded-lg border text-base font-medium">
                            ${escapeHtml(coupleLabel)}
                        </button>
                    </div>
                    <div id="catalog-consultation-hidden-inputs" class="hidden"></div>
                    <p class="text-xs text-gray-400">
                        Можно оставить оба варианта невыбранными — это режим "все специалисты".
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

            const consultationBlock = document.getElementById("catalog-consultation-block");
            if (consultationBlock) {
                consultationBlock.addEventListener("click", (event) => {
                    if (!event.target.closest(".catalog-consultation-btn")) return;

                    window.requestAnimationFrame(() => {
                        scheduleApplyButtonPreviewRefresh();
                    });
                });
            }

            scheduleApplyButtonPreviewRefresh();
            return;
        }

        if (filterName === "Симптомы") {
            const selectedTopicIds = normalizeTopicIds(catalogRuntimeState.filters.topic_ids);
            modalContent.innerHTML = buildTopicsModalHtml(selectedTopicIds);

            initCollapsibleTopicGroups({
                rootSelector: "#catalog-topic-groups-root",
                visibleCount: 0,
            });

            const topicsRoot = document.getElementById("catalog-topic-groups-root");
            if (topicsRoot) {
                topicsRoot.addEventListener("change", (event) => {
                    if (!event.target.closest(".catalog-topic-checkbox")) return;
                    scheduleApplyButtonPreviewRefresh();
                });
            }

            scheduleApplyButtonPreviewRefresh();
            return;
        }

        modalContent.innerHTML = `
            <p class="text-sm text-gray-500 leading-relaxed">
                Этот фильтр будет подключен на следующем шаге. Сейчас можно закрыть модалку.
            </p>
        `;
        applyButton.textContent = APPLY_RESULTS_LABEL;
    }

    async function applyCurrentFilter() {
        if (openedFilterName === "Вид консультации") {
            const isApplied = await applyCatalogFilters({
                consultation_type: getModalSelectedConsultationType(),
            });
            if (isApplied) closeModal();
            return;
        }

        if (openedFilterName === "Симптомы") {
            const isApplied = await applyCatalogFilters({
                topic_ids: getModalSelectedTopicIds(),
            });
            if (isApplied) closeModal();
            return;
        }

        closeModal();
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
