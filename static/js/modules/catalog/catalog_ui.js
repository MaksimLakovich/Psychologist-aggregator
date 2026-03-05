import { pluralizeRu } from "../utils/pluralize_ru.js";
import {
    APPLY_RESULTS_LABEL,
    PREVIEW_RESULTS_LABEL,
    catalogRuntimeState,
    getLoadMoreButton,
} from "./catalog_page_runtime.js";
import { getCatalogFilterConfig, getCatalogFilterChipConfigs } from "./catalog_filter_registry.js";
import {
    toNonNegativeInt,
    toPositiveInt,
} from "./catalog_state.js";

/**
 * UI-слой каталога.
 *
 * Здесь живут только функции рендера и инициализации DOM-элементов,
 * без knowledge о transport-слое и restore-flow.
 */

// Унифицирует рендер подписи под кнопкой применения фильтра.
// Это убирает дублирование шаблона кнопки для состояний "идет подсчет" и "показываем количество результатов".
export function renderApplyButtonState(applyButton, detailsText) {
    if (!applyButton) return;

    applyButton.innerHTML = `
        ${APPLY_RESULTS_LABEL}
        <span class="block mt-1 text-xs font-medium text-indigo-100">
            ${detailsText}
        </span>
    `;
}

// Перерисовывает текст кнопки применения фильтра с количеством найденных специалистов.
export function renderApplyButtonWithCount(applyButton, totalCount) {
    const safeCount = toNonNegativeInt(totalCount, 0);
    const specialistWord = pluralizeRu(safeCount, "специалист", "специалиста", "специалистов");

    renderApplyButtonState(applyButton, `Найдено: ${safeCount} ${specialistWord}`);
}

// Показывает на кнопке применения фильтра состояние "идет подсчет".
export function renderApplyButtonLoading(applyButton) {
    renderApplyButtonState(applyButton, PREVIEW_RESULTS_LABEL);
}

// Подсвечивает активные чипы фильтров на странице.
// Каждый фильтр сам сообщает, активен он сейчас или нет, а UI-слой только применяет нужные классы.
export function renderFilterChipStates() {
    document.querySelectorAll("[data-filter-chip]").forEach((chip) => {
        const filterKey = chip.dataset.filterKey || "";
        const filterConfig = getCatalogFilterConfig(filterKey);
        const isActive = filterConfig ? filterConfig.isActive(catalogRuntimeState.filters) : false;

        chip.classList.toggle("bg-indigo-200/40", isActive);
        chip.classList.toggle("text-indigo-700", isActive);
        chip.classList.toggle("bg-slate-200/40", !isActive);
        chip.classList.toggle("text-slate-600", !isActive);
    });
}

// Проверяет, есть ли в каталоге хотя бы один реально активный фильтр.
function hasActiveCatalogFilters(filters) {
    return getCatalogFilterChipConfigs().some((filterConfig) => filterConfig.isActive(filters));
}

// Обновляет состояние кнопки "Сбросить фильтры".
// Когда фильтры не установлены, делаем кнопку неактивной и визуально спокойной.
export function renderResetFiltersButtonState() {
    const resetButton = document.getElementById("catalog-reset-filters-btn");
    if (!resetButton) return;

    resetButton.disabled = !hasActiveCatalogFilters(catalogRuntimeState.filters);
}

// Обновляет текстовый индикатор текущей страницы каталога.
export function renderCurrentPageIndicator(currentPage, totalPages) {
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

// Обновляет кнопку "Показать еще" после ответа сервера.
export function syncLoadMoreButton(data) {
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

// Показывает или скрывает пустое состояние каталога.
export function renderEmptyState(totalCount) {
    const emptyState = document.getElementById("catalog-empty-state");
    if (!emptyState) return;

    emptyState.classList.toggle("hidden", toNonNegativeInt(totalCount, 0) > 0);
}

// Инициализирует вкладки внутри карточек каталога.
// Карточки могут прийти и с SSR, и через AJAX, поэтому эту функцию можно безопасно запускать повторно.
export function initCardTabs(scope = document) {
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

// Инициализирует кнопку "В начало".
export function initScrollToTopButton() {
    const scrollTopButton = document.getElementById("catalog-scroll-top-btn");
    if (!scrollTopButton) return;

    scrollTopButton.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
}
