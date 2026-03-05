import {
    APPLY_RESULTS_LABEL,
    buildDefaultCatalogFilters,
    catalogRuntimeState,
    getLoadMoreButton,
    hydrateRuntimeStateFromDom,
    normalizeCatalogFilters,
} from "./catalog_page_runtime.js";
import {
    getCatalogFilterConfig,
    renderCatalogFilterChips,
} from "./catalog_filter_registry.js";
import { requestCatalogData } from "./catalog_api.js";
import {
    initCardTabs,
    initScrollToTopButton,
    renderApplyButtonLoading,
    renderApplyButtonWithCount,
    renderCurrentPageIndicator,
    renderEmptyState,
    renderFilterChipStates,
    renderResetFiltersButtonState,
    syncLoadMoreButton,
} from "./catalog_ui.js";
import {
    initCatalogStatePersistence,
    persistCatalogState,
    restoreCatalogIfNeeded,
} from "./catalog_restore.js";
import {
    toNonNegativeInt,
    toPositiveInt,
} from "./catalog_state.js";

/**
 * Оркестратор страницы каталога психологов.
 *
 * Здесь остается только page-level координация:
 * - модалка фильтров;
 * - применение фильтров;
 * - догрузка карточек;
 * - запуск restore-flow и инициализации страницы.
 */

// Храним id последнего preview-запроса, чтобы старый ответ не перерисовал кнопку поверх нового состояния модалки.
let activePreviewRequestId = 0;

// Применяет ответ сервера к интерфейсу каталога.
// В обычном режиме полностью заменяем карточки, а в режиме appendMode добавляем новую страницу карточек вниз.
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
    renderResetFiltersButtonState();
    persistCatalogState();
}

// Применяет изменения фильтров каталога и запрашивает новую первую страницу.
// Если запрос завершился ошибкой, возвращаем прежнее состояние фильтров и положения страницы.
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

// Инициализирует общую модалку фильтров каталога.
// Здесь живет только оболочка модалки и диспетчеризация, а контент конкретных фильтров остается в catalog_filter_*.js.
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

    let openedFilterConfig = null;
    let previewDebounceTimer = null;

    function clearPreviewRefreshTimer() {
        if (!previewDebounceTimer) return;

        window.clearTimeout(previewDebounceTimer);
        previewDebounceTimer = null;
    }

    function closeModal() {
        clearPreviewRefreshTimer();
        openedFilterConfig = null;
        modal.classList.add("hidden");
        modal.classList.remove("flex");
        document.body.style.overflow = "";
    }

    function renderOpenedFilterModal() {
        if (!openedFilterConfig) return;

        openedFilterConfig.renderModal({
            modalContent,
            schedulePreviewRefresh,
        });
        schedulePreviewRefresh();
    }

    function openModal(filterButton) {
        const filterKey = filterButton.dataset.filterKey || "";

        openedFilterConfig = getCatalogFilterConfig(filterKey);
        if (!openedFilterConfig) return;

        modalTitle.textContent = openedFilterConfig.name;
        renderOpenedFilterModal();
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        document.body.style.overflow = "hidden";
    }

    function buildTentativeFiltersForOpenedModal() {
        if (!openedFilterConfig) {
            return normalizeCatalogFilters(catalogRuntimeState.filters);
        }

        return openedFilterConfig.buildTentativeFilters();
    }

    function refreshApplyButtonPreview() {
        const requestId = ++activePreviewRequestId;
        renderApplyButtonLoading(applyButton);

        requestCatalogData({
            previewOnly: true,
            filtersOverride: buildTentativeFiltersForOpenedModal(),
        }).then((previewData) => {
            if (requestId !== activePreviewRequestId) return;
            renderApplyButtonWithCount(applyButton, previewData.total_count);
        }).catch((error) => {
            if (requestId !== activePreviewRequestId) return;
            console.error("Ошибка preview-count каталога:", error);
            applyButton.textContent = APPLY_RESULTS_LABEL;
        });
    }

    function schedulePreviewRefresh() {
        clearPreviewRefreshTimer();
        previewDebounceTimer = window.setTimeout(() => {
            refreshApplyButtonPreview();
        }, 180);
    }

    async function applyOpenedFilter() {
        if (!openedFilterConfig) {
            closeModal();
            return;
        }

        const isApplied = await applyCatalogFilters(openedFilterConfig.readModalFilters());
        if (isApplied) {
            closeModal();
        }
    }

    filterButtons.forEach((button) => {
        button.addEventListener("click", () => {
            openModal(button);
        });
    });

    modalOverlay.addEventListener("click", closeModal);
    closeButton.addEventListener("click", closeModal);
    applyButton.addEventListener("click", applyOpenedFilter);

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !modal.classList.contains("hidden")) {
            closeModal();
        }
    });
}

// Инициализирует кнопку "Показать еще" для догрузки следующих страниц каталога.
function initLoadMore() {
    const loadMoreButton = getLoadMoreButton();
    const errorLabel = document.getElementById("catalog-load-more-error");

    if (!loadMoreButton) return;

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

// Инициализирует кнопку "Сбросить фильтры".
// При нажатии возвращаем каталог к начальному состоянию: все фильтры снимаются и снова показываются все специалисты.
function initResetFiltersButton() {
    const resetButton = document.getElementById("catalog-reset-filters-btn");
    const errorLabel = document.getElementById("catalog-load-more-error");
    if (!resetButton) return;

    renderResetFiltersButtonState();

    resetButton.addEventListener("click", async () => {
        if (resetButton.disabled) return;

        resetButton.disabled = true;
        if (errorLabel) {
            errorLabel.classList.add("hidden");
        }

        const isApplied = await applyCatalogFilters(buildDefaultCatalogFilters());
        if (!isApplied) {
            renderResetFiltersButtonState();
            return;
        }

        catalogRuntimeState.anchor = null;
        catalogRuntimeState.scroll_y = 0;
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
}

// Общая точка инициализации страницы каталога.
// Здесь запускаем весь page-level функционал в правильном порядке.
export async function bootstrapCatalogPage() {
    hydrateRuntimeStateFromDom();
    renderCatalogFilterChips();
    renderCurrentPageIndicator(catalogRuntimeState.current_page, catalogRuntimeState.total_pages);
    renderFilterChipStates();

    initCatalogFiltersModal();
    initCardTabs();
    initLoadMore();
    initScrollToTopButton();
    initResetFiltersButton();

    await restoreCatalogIfNeeded({
        requestCatalogData,
        applyCatalogResponse,
    });
    initCatalogStatePersistence();
}
