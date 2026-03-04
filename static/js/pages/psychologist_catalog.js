import {
    clearCatalogState,
    consumeCatalogRestorePending,
    readCatalogState,
    toNonNegativeInt,
    toPositiveInt,
    writeCatalogState,
} from "../modules/catalog_state.js";
import { pluralizeRu } from "../utils/pluralize_ru.js";
import {
    buildCatalogAgeTentativeFilters,
    CATALOG_AGE_FILTER_KEY,
    CATALOG_AGE_FILTER_NAME,
    getCatalogAgeModalValues,
    isCatalogAgeFilterActive,
    normalizeCatalogAgeRange,
    renderCatalogAgeModal,
} from "../modules/catalog_filter_age.js";
import {
    buildCatalogExperienceTentativeFilters,
    CATALOG_EXPERIENCE_FILTER_KEY,
    CATALOG_EXPERIENCE_FILTER_NAME,
    getCatalogExperienceModalValues,
    isCatalogExperienceFilterActive,
    normalizeCatalogExperienceRange,
    renderCatalogExperienceModal,
} from "../modules/catalog_filter_experience.js";
import {
    buildCatalogGenderTentativeFilters,
    CATALOG_GENDER_FILTER_KEY,
    CATALOG_GENDER_FILTER_NAME,
    getCatalogGenderModalValue,
    isCatalogGenderFilterActive,
    normalizeCatalogGender,
    renderCatalogGenderModal,
} from "../modules/catalog_filter_gender.js";
import {
    buildCatalogMethodsTentativeFilters,
    CATALOG_METHODS_FILTER_KEY,
    CATALOG_METHODS_FILTER_NAME,
    getCatalogMethodsModalValues,
    isCatalogMethodsFilterActive,
    normalizeCatalogMethodIds,
    renderCatalogMethodsModal,
} from "../modules/catalog_filter_methods.js";
import {
    buildCatalogTopicTypeTentativeFilters,
    CATALOG_TOPIC_TYPE_FILTER_KEY,
    CATALOG_TOPIC_TYPE_FILTER_NAME,
    getCatalogTopicTypeModalValue,
    isCatalogTopicTypeFilterActive,
    normalizeCatalogTopicType,
    renderCatalogTopicTypeModal,
} from "../modules/catalog_filter_topic_type.js";
import {
    buildCatalogTopicsTentativeFilters,
    CATALOG_TOPICS_FILTER_KEY,
    CATALOG_TOPICS_FILTER_NAME,
    filterCatalogTopicIdsByConsultationType,
    getCatalogTopicsModalValues,
    isCatalogTopicsFilterActive,
    normalizeCatalogTopicIds,
    renderCatalogTopicsModal,
} from "../modules/catalog_filter_topics.js";
import {
    buildCatalogPriceTentativeFilters,
    CATALOG_PRICE_FILTER_KEY,
    CATALOG_PRICE_FILTER_NAME,
    getCatalogPriceModalValues,
    isCatalogPriceFilterActive,
    normalizeCatalogPriceFilters,
    renderCatalogPriceModal,
} from "../modules/catalog_filter_price.js";
import {
    buildCatalogSessionTimeTentativeFilters,
    CATALOG_SESSION_TIME_FILTER_KEY,
    CATALOG_SESSION_TIME_FILTER_NAME,
    getCatalogSessionTimeModalMode,
    getCatalogSessionTimeModalSelectedSlots,
    isCatalogSessionTimeFilterActive,
    normalizeCatalogSelectedSessionSlots,
    normalizeCatalogSessionTimeMode,
    renderCatalogSessionTimeModal,
} from "../modules/catalog_filter_session_time.js";

/**
 * Главный файл страницы каталога психологов.
 *
 * Бизнес-задача этого файла:
 * - координировать работу страницы каталога целиком;
 * - хранить временное runtime-state текущей вкладки;
 * - выполнять AJAX-фильтрацию и догрузку карточек;
 * - подключать отдельные модули фильтров catalog_filter_*.js;
 * - восстанавливать каталог после возврата из detail.
 *
 * Важно:
 * - детали каждого фильтра вынесены в отдельные модули;
 * - здесь остается только общая инфраструктура страницы и диспетчеризация.
 */

const APPLY_RESULTS_LABEL = "Показать результаты";
const PREVIEW_RESULTS_LABEL = "Считаем результаты...";

// Временное состояние каталога для текущей вкладки браузера.
// Это не БД и не server session, а только рабочие данные текущего сценария пользователя.
const catalogRuntimeState = {
    layout_mode: "menu",
    current_page: 1,
    total_pages: 0,
    order_key: null,
    anchor: null,
    scroll_y: 0,
    filters: {},
};

// Храним id последнего preview-запроса, чтобы старый ответ не перерисовал кнопку поверх нового состояния модалки.
let activePreviewRequestId = 0;

// Возвращает дефолтное состояние всех фильтров каталога.
// Это один общий источник правды для первого рендера страницы и для кнопки "Сбросить фильтры".
function buildDefaultCatalogFilters() {
    return {
        consultation_type: null,
        topic_ids: [],
        method_ids: [],
        gender: null,
        price_individual_values: [],
        price_couple_values: [],
        age_min: null,
        age_max: null,
        experience_min: null,
        experience_max: null,
        session_time_mode: "any",
        selected_session_slots: [],
    };
}

catalogRuntimeState.filters = buildDefaultCatalogFilters();

// Преобразует текст в безопасный HTML.
// Это нужно, потому что часть текста приходит из БД и не должна вставляться в DOM как сырой HTML.
function escapeHtml(value) {
    const sourceValue = String(value ?? "");

    return sourceValue
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\"", "&quot;")
        .replaceAll("'", "&#39;");
}

// Безопасно читает JSON из json_script.
// Если данных нет или JSON поврежден, возвращаем fallback, чтобы страница не ломалась.
function readJsonScript(id, fallback) {
    const scriptTag = document.getElementById(id);
    if (!scriptTag) return fallback;

    try {
        return JSON.parse(scriptTag.textContent || "null") ?? fallback;
    } catch (error) {
        return fallback;
    }
}

// Приводит объект фильтров к единому предсказуемому формату.
// Это общая точка нормализации всех фильтров каталога: по мере добавления новых фильтров они должны подключаться именно здесь.
function normalizeCatalogFilters(rawFilters = {}) {
    const consultationType = normalizeCatalogTopicType(rawFilters?.consultation_type, { readJsonScript });
    const topicIds = filterCatalogTopicIdsByConsultationType({
        topicIds: normalizeCatalogTopicIds(rawFilters?.topic_ids),
        consultationType,
        readJsonScript,
    });
    const methodIds = normalizeCatalogMethodIds(rawFilters?.method_ids);
    const gender = normalizeCatalogGender(rawFilters?.gender, { readJsonScript });
    const normalizedPriceFilters = normalizeCatalogPriceFilters({
        consultationType,
        priceIndividualValues: rawFilters?.price_individual_values,
        priceCoupleValues: rawFilters?.price_couple_values,
        readJsonScript,
    });
    const ageRange = normalizeCatalogAgeRange(rawFilters?.age_min, rawFilters?.age_max, { readJsonScript });
    const experienceRange = normalizeCatalogExperienceRange(
        rawFilters?.experience_min,
        rawFilters?.experience_max,
        { readJsonScript },
    );
    const sessionTimeMode = normalizeCatalogSessionTimeMode(rawFilters?.session_time_mode);
    const selectedSessionSlots = normalizeCatalogSelectedSessionSlots(rawFilters?.selected_session_slots);

    return {
        consultation_type: consultationType,
        topic_ids: topicIds,
        method_ids: methodIds,
        gender,
        price_individual_values: normalizedPriceFilters.price_individual_values,
        price_couple_values: normalizedPriceFilters.price_couple_values,
        age_min: ageRange.age_min,
        age_max: ageRange.age_max,
        experience_min: experienceRange.experience_min,
        experience_max: experienceRange.experience_max,
        session_time_mode: sessionTimeMode,
        selected_session_slots: selectedSessionSlots,
    };
}

// Описывает подключенные фильтры каталога.
// Каждый фильтр сам знает, как отрисовать свою модалку, как собрать временное состояние и как прочитать выбранные пользователем значения.
const CATALOG_FILTER_REGISTRY = {
    [CATALOG_TOPIC_TYPE_FILTER_KEY]: {
        key: CATALOG_TOPIC_TYPE_FILTER_KEY,
        name: CATALOG_TOPIC_TYPE_FILTER_NAME,
        isActive(filters) {
            return isCatalogTopicTypeFilterActive(filters, { readJsonScript });
        },
        renderModal({ modalContent, schedulePreviewRefresh }) {
            renderCatalogTopicTypeModal({
                modalContent,
                catalogRuntimeState,
                schedulePreviewRefresh,
                escapeHtml,
                readJsonScript,
            });
        },
        buildTentativeFilters() {
            return buildCatalogTopicTypeTentativeFilters({
                catalogRuntimeState,
                normalizeCatalogFilters,
                readJsonScript,
            });
        },
        readModalFilters() {
            return {
                consultation_type: getCatalogTopicTypeModalValue({ readJsonScript }),
            };
        },
    },
    [CATALOG_TOPICS_FILTER_KEY]: {
        key: CATALOG_TOPICS_FILTER_KEY,
        name: CATALOG_TOPICS_FILTER_NAME,
        isActive(filters) {
            return isCatalogTopicsFilterActive(filters);
        },
        renderModal({ modalContent, schedulePreviewRefresh }) {
            renderCatalogTopicsModal({
                modalContent,
                catalogRuntimeState,
                schedulePreviewRefresh,
                escapeHtml,
                readJsonScript,
            });
        },
        buildTentativeFilters() {
            return buildCatalogTopicsTentativeFilters({
                catalogRuntimeState,
                normalizeCatalogFilters,
            });
        },
        readModalFilters() {
            return {
                topic_ids: getCatalogTopicsModalValues(),
            };
        },
    },
    [CATALOG_METHODS_FILTER_KEY]: {
        key: CATALOG_METHODS_FILTER_KEY,
        name: CATALOG_METHODS_FILTER_NAME,
        isActive(filters) {
            return isCatalogMethodsFilterActive(filters);
        },
        renderModal({ modalContent, schedulePreviewRefresh }) {
            renderCatalogMethodsModal({
                modalContent,
                catalogRuntimeState,
                schedulePreviewRefresh,
                escapeHtml,
                readJsonScript,
            });
        },
        buildTentativeFilters() {
            return buildCatalogMethodsTentativeFilters({
                catalogRuntimeState,
                normalizeCatalogFilters,
            });
        },
        readModalFilters() {
            return {
                method_ids: getCatalogMethodsModalValues(),
            };
        },
    },
    [CATALOG_GENDER_FILTER_KEY]: {
        key: CATALOG_GENDER_FILTER_KEY,
        name: CATALOG_GENDER_FILTER_NAME,
        isActive(filters) {
            return isCatalogGenderFilterActive(filters, { readJsonScript });
        },
        renderModal({ modalContent, schedulePreviewRefresh }) {
            renderCatalogGenderModal({
                modalContent,
                catalogRuntimeState,
                schedulePreviewRefresh,
                escapeHtml,
                readJsonScript,
            });
        },
        buildTentativeFilters() {
            return buildCatalogGenderTentativeFilters({
                catalogRuntimeState,
                normalizeCatalogFilters,
                readJsonScript,
            });
        },
        readModalFilters() {
            return {
                gender: getCatalogGenderModalValue({ readJsonScript }),
            };
        },
    },
    [CATALOG_PRICE_FILTER_KEY]: {
        key: CATALOG_PRICE_FILTER_KEY,
        name: CATALOG_PRICE_FILTER_NAME,
        isActive(filters) {
            return isCatalogPriceFilterActive(filters, { readJsonScript });
        },
        renderModal({ modalContent, schedulePreviewRefresh }) {
            renderCatalogPriceModal({
                modalContent,
                catalogRuntimeState,
                schedulePreviewRefresh,
                escapeHtml,
                readJsonScript,
            });
        },
        buildTentativeFilters() {
            return buildCatalogPriceTentativeFilters({
                catalogRuntimeState,
                normalizeCatalogFilters,
                readJsonScript,
            });
        },
        readModalFilters() {
            return getCatalogPriceModalValues({
                consultationType: catalogRuntimeState.filters.consultation_type,
                readJsonScript,
            });
        },
    },
    [CATALOG_AGE_FILTER_KEY]: {
        key: CATALOG_AGE_FILTER_KEY,
        name: CATALOG_AGE_FILTER_NAME,
        isActive(filters) {
            return isCatalogAgeFilterActive(filters, { readJsonScript });
        },
        renderModal({ modalContent, schedulePreviewRefresh }) {
            renderCatalogAgeModal({
                modalContent,
                catalogRuntimeState,
                schedulePreviewRefresh,
                readJsonScript,
            });
        },
        buildTentativeFilters() {
            return buildCatalogAgeTentativeFilters({
                catalogRuntimeState,
                normalizeCatalogFilters,
                readJsonScript,
            });
        },
        readModalFilters() {
            return getCatalogAgeModalValues({ readJsonScript });
        },
    },
    [CATALOG_EXPERIENCE_FILTER_KEY]: {
        key: CATALOG_EXPERIENCE_FILTER_KEY,
        name: CATALOG_EXPERIENCE_FILTER_NAME,
        isActive(filters) {
            return isCatalogExperienceFilterActive(filters, { readJsonScript });
        },
        renderModal({ modalContent, schedulePreviewRefresh }) {
            renderCatalogExperienceModal({
                modalContent,
                catalogRuntimeState,
                schedulePreviewRefresh,
                readJsonScript,
            });
        },
        buildTentativeFilters() {
            return buildCatalogExperienceTentativeFilters({
                catalogRuntimeState,
                normalizeCatalogFilters,
                readJsonScript,
            });
        },
        readModalFilters() {
            return getCatalogExperienceModalValues({ readJsonScript });
        },
    },
    [CATALOG_SESSION_TIME_FILTER_KEY]: {
        key: CATALOG_SESSION_TIME_FILTER_KEY,
        name: CATALOG_SESSION_TIME_FILTER_NAME,
        isActive(filters) {
            return isCatalogSessionTimeFilterActive(filters);
        },
        renderModal({ modalContent, schedulePreviewRefresh }) {
            renderCatalogSessionTimeModal({
                modalContent,
                catalogRuntimeState,
                schedulePreviewRefresh,
                domainSlotsEndpoint: resolveCatalogDomainSlotsEndpoint(),
            });
        },
        buildTentativeFilters() {
            return buildCatalogSessionTimeTentativeFilters({
                catalogRuntimeState,
                normalizeCatalogFilters,
            });
        },
        readModalFilters() {
            return {
                session_time_mode: getCatalogSessionTimeModalMode(),
                selected_session_slots: getCatalogSessionTimeModalSelectedSlots(),
            };
        },
    },
};

// Возвращает конфиг поддерживаемого фильтра по ключу или имени.
// По ключу ищем в первую очередь, а по имени используем fallback для кнопок, у которых ключа пока нет.
function getCatalogFilterConfig({ filterKey = "", filterName = "" } = {}) {
    if (filterKey && CATALOG_FILTER_REGISTRY[filterKey]) {
        return CATALOG_FILTER_REGISTRY[filterKey];
    }

    return Object.values(CATALOG_FILTER_REGISTRY).find((config) => config.name === filterName) || null;
}

// Возвращает кнопку "Показать еще".
// В ее data-атрибутах лежит часть стартового состояния каталога.
function getLoadMoreButton() {
    return document.getElementById("catalog-load-more-btn");
}

// Возвращает AJAX-endpoint каталога.
function resolveCatalogFilterEndpoint() {
    const loadMoreButton = getLoadMoreButton();
    return loadMoreButton?.dataset.filterEndpoint || "";
}

// Возвращает read-only endpoint доменных слотов для фильтра "Время сессии".
function resolveCatalogDomainSlotsEndpoint() {
    const loadMoreButton = getLoadMoreButton();
    return loadMoreButton?.dataset.domainSlotsEndpoint || "";
}

// Собирает заголовки для POST-запросов каталога.
function buildCatalogRequestHeaders() {
    return {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": window.CSRF_TOKEN || "",
    };
}

// Делает AJAX-запрос к backend и возвращает JSON-ответ каталога.
// Один и тот же endpoint используем для preview-count, применения фильтров, догрузки карточек и восстановления каталога после detail.
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

// Перерисовывает текст кнопки применения фильтра с количеством найденных специалистов.
function renderApplyButtonWithCount(applyButton, totalCount) {
    if (!applyButton) return;

    const safeCount = toNonNegativeInt(totalCount, 0);
    const specialistWord = pluralizeRu(safeCount, "специалист", "специалиста", "специалистов");

    applyButton.innerHTML = `
        ${APPLY_RESULTS_LABEL}
        <span class="block mt-1 text-xs font-medium text-indigo-100">
            Найдено: ${safeCount} ${specialistWord}
        </span>
    `;
}

// Показывает на кнопке применения фильтра состояние "идет подсчет".
function renderApplyButtonLoading(applyButton) {
    if (!applyButton) return;

    applyButton.innerHTML = `
        ${APPLY_RESULTS_LABEL}
        <span class="block mt-1 text-xs font-medium text-indigo-100">
            ${PREVIEW_RESULTS_LABEL}
        </span>
    `;
}

// Подсвечивает активные чипы фильтров на странице.
// Каждый фильтр сам сообщает, активен он сейчас или нет, а page-файл только применяет нужные классы.
function renderFilterChipStates() {
    document.querySelectorAll("[data-filter-chip]").forEach((chip) => {
        const filterKey = chip.dataset.filterKey || "";
        const filterName = chip.dataset.filterName || "";
        const filterConfig = getCatalogFilterConfig({ filterKey, filterName });
        const isActive = filterConfig ? filterConfig.isActive(catalogRuntimeState.filters) : false;

        chip.classList.toggle("bg-indigo-200/40", isActive);
        chip.classList.toggle("text-indigo-700", isActive);
        chip.classList.toggle("bg-slate-200/40", !isActive);
        chip.classList.toggle("text-slate-600", !isActive);
    });
}

// Проверяет, есть ли в каталоге хотя бы один реально активный фильтр.
// Это нужно для кнопки "Сбросить фильтры", чтобы она была активна только тогда, когда сбрасывать действительно есть что.
function hasActiveCatalogFilters(filters) {
    return Object.values(CATALOG_FILTER_REGISTRY).some((filterConfig) => filterConfig.isActive(filters));
}

// Обновляет состояние кнопки "Сбросить фильтры".
// Когда фильтры не установлены, делаем кнопку неактивной и визуально спокойной.
function renderResetFiltersButtonState() {
    const resetButton = document.getElementById("catalog-reset-filters-btn");
    if (!resetButton) return;

    resetButton.disabled = !hasActiveCatalogFilters(catalogRuntimeState.filters);
}

// Обновляет текстовый индикатор текущей страницы каталога.
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

// Обновляет кнопку "Показать еще" после ответа сервера.
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

// Показывает или скрывает пустое состояние каталога.
function renderEmptyState(totalCount) {
    const emptyState = document.getElementById("catalog-empty-state");
    if (!emptyState) return;

    emptyState.classList.toggle("hidden", toNonNegativeInt(totalCount, 0) > 0);
}

// Инициализирует вкладки внутри карточек каталога.
// Карточки могут прийти и с SSR, и через AJAX, поэтому эту функцию можно безопасно запускать повторно.
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

// Считывает стартовое состояние каталога из data-атрибутов страницы.
function hydrateRuntimeStateFromDom() {
    const loadMoreButton = getLoadMoreButton();
    if (!loadMoreButton) return;

    catalogRuntimeState.layout_mode = loadMoreButton.dataset.layout === "sidebar" ? "sidebar" : "menu";
    catalogRuntimeState.current_page = toPositiveInt(loadMoreButton.dataset.currentPage, 1);
    catalogRuntimeState.total_pages = toNonNegativeInt(loadMoreButton.dataset.totalPages, 0);
    catalogRuntimeState.order_key = toNonNegativeInt(loadMoreButton.dataset.randomOrderKey, null);
    catalogRuntimeState.filters = normalizeCatalogFilters(buildDefaultCatalogFilters());
}

// Сохраняет текущее состояние каталога в sessionStorage.
// Это временная резервная копия для сценария возврата из detail.
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

// Восстанавливает позицию прокрутки после возврата из detail.
// Сначала пробуем вернуться к конкретной карточке, а если не получилось, используем сохраненную координату прокрутки.
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
// Здесь живет только оболочка модалки и диспетчеризация, а контент и бизнес-логика конкретных фильтров остаются в catalog_filter_*.js.
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

    // Останавливает отложенный пересчет preview-count, если пользователь уже закрыл модалку или быстро переключил состояние.
    function clearPreviewRefreshTimer() {
        if (!previewDebounceTimer) return;

        window.clearTimeout(previewDebounceTimer);
        previewDebounceTimer = null;
    }

    // Закрывает модалку и возвращает обычный скролл основной странице.
    function closeModal() {
        clearPreviewRefreshTimer();
        openedFilterConfig = null;
        modal.classList.add("hidden");
        modal.classList.remove("flex");
        document.body.style.overflow = "";
    }

    // Открывает модалку для выбранного фильтра и передает управление нужному filter-модулю.
    function openModal(filterButton) {
        const filterKey = filterButton.dataset.filterKey || "";
        const filterName = filterButton.dataset.filterName || "Фильтр";

        openedFilterConfig = getCatalogFilterConfig({ filterKey, filterName });
        if (!openedFilterConfig) return;

        modalTitle.textContent = filterName;
        renderOpenedFilterModal();
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        document.body.style.overflow = "hidden";
    }

    // Собирает временное состояние фильтров для preview-count по открытому сейчас фильтру.
    function buildTentativeFiltersForOpenedModal() {
        if (!openedFilterConfig) {
            return normalizeCatalogFilters(catalogRuntimeState.filters);
        }

        return openedFilterConfig.buildTentativeFilters();
    }

    // Запрашивает у backend количество результатов для текущего состояния открытой модалки.
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

    // Запускает пересчет preview-count с небольшим debounce.
    // Это уменьшает число лишних запросов, когда пользователь быстро кликает по фильтру.
    function schedulePreviewRefresh() {
        clearPreviewRefreshTimer();
        previewDebounceTimer = window.setTimeout(() => {
            refreshApplyButtonPreview();
        }, 180);
    }

    // Отрисовывает контент для открытого фильтра.
    // В этот момент конфиг фильтра уже найден, поэтому здесь остается только вызвать нужный filter-модуль и обновить preview-count.
    function renderOpenedFilterModal() {
        openedFilterConfig.renderModal({
            modalContent,
            schedulePreviewRefresh,
        });
        schedulePreviewRefresh();
    }

    // Применяет изменения из открытой модалки к каталогу.
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

// Инициализирует кнопку "В начало".
function initScrollToTopButton() {
    const scrollTopButton = document.getElementById("catalog-scroll-top-btn");
    if (!scrollTopButton) return;

    scrollTopButton.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
}

// Инициализирует нижнюю drag-полоску для горизонтального ряда фильтров.
// Бизнес-смысл: даем пользователю понятную область, которую можно "схватить" мышкой и протянуть влево-вправо.
function initCatalogFilterDragTrack() {
    const scroller = document.getElementById("catalog-filter-scroll-area");
    const dragTrack = document.getElementById("catalog-filter-drag-track");
    const dragThumb = document.getElementById("catalog-filter-drag-thumb");
    if (!scroller || !dragTrack || !dragThumb) return;

    let isDragging = false;

    // Синхронизирует ширину и положение бегунка с реальным горизонтальным скроллом ряда фильтров.
    function syncDragThumb() {
        const maxScrollLeft = Math.max(scroller.scrollWidth - scroller.clientWidth, 0);
        const hasOverflow = maxScrollLeft > 0;

        dragTrack.classList.toggle("hidden", !hasOverflow);
        if (!hasOverflow) {
            dragThumb.style.width = "100%";
            dragThumb.style.transform = "translateX(0)";
            return;
        }

        const trackWidth = dragTrack.clientWidth;
        const visibleRatio = scroller.clientWidth / scroller.scrollWidth;
        const thumbWidth = Math.max(trackWidth * visibleRatio, 48);
        const maxThumbOffset = Math.max(trackWidth - thumbWidth, 0);
        const thumbOffset = maxScrollLeft > 0
            ? (scroller.scrollLeft / maxScrollLeft) * maxThumbOffset
            : 0;

        dragThumb.style.width = `${thumbWidth}px`;
        dragThumb.style.transform = `translateX(${thumbOffset}px)`;
    }

    // Переводит позицию курсора внутри полоски в scrollLeft реального ряда фильтров.
    function updateScrollFromPointer(clientX) {
        const trackRect = dragTrack.getBoundingClientRect();
        const maxScrollLeft = Math.max(scroller.scrollWidth - scroller.clientWidth, 0);
        if (trackRect.width <= 0 || maxScrollLeft <= 0) return;

        const thumbWidth = dragThumb.offsetWidth;
        const maxThumbOffset = Math.max(trackRect.width - thumbWidth, 0);
        const rawOffset = clientX - trackRect.left - thumbWidth / 2;
        const boundedOffset = Math.min(Math.max(rawOffset, 0), maxThumbOffset);
        const scrollRatio = maxThumbOffset > 0 ? boundedOffset / maxThumbOffset : 0;

        scroller.scrollLeft = scrollRatio * maxScrollLeft;
    }

    dragTrack.addEventListener("pointerdown", (event) => {
        isDragging = true;
        dragTrack.classList.add("is-dragging");
        dragTrack.setPointerCapture(event.pointerId);
        updateScrollFromPointer(event.clientX);
    });

    dragTrack.addEventListener("pointermove", (event) => {
        if (!isDragging) return;
        updateScrollFromPointer(event.clientX);
    });

    function stopDragging(event) {
        if (!isDragging) return;
        isDragging = false;
        dragTrack.classList.remove("is-dragging");
        if (typeof event.pointerId !== "undefined") {
            dragTrack.releasePointerCapture(event.pointerId);
        }
    }

    dragTrack.addEventListener("pointerup", stopDragging);
    dragTrack.addEventListener("pointercancel", stopDragging);
    scroller.addEventListener("scroll", syncDragThumb, { passive: true });
    window.addEventListener("resize", syncDragThumb);

    syncDragThumb();
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

// Сохраняет состояние каталога перед переходом в detail.
// Это нужно, чтобы потом можно было вернуть пользователя на тот же набор карточек и к той же позиции.
function initCatalogStatePersistence() {
    document.addEventListener("click", (event) => {
        const detailLink = event.target.closest("[data-catalog-detail-link]");
        if (!detailLink) return;

        catalogRuntimeState.anchor = detailLink.dataset.profileSlug || null;
        catalogRuntimeState.scroll_y = Math.max(window.scrollY, 0);
        persistCatalogState();
    });
}

// Пытается восстановить каталог после возврата из detail.
// Если пользователь открыл каталог заново, а не вернулся назад из detail, старое состояние очищаем и не применяем.
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

// Общая точка инициализации страницы каталога.
// Здесь запускаем весь page-level функционал в правильном порядке.
async function bootstrapCatalogPage() {
    hydrateRuntimeStateFromDom();
    renderCurrentPageIndicator(catalogRuntimeState.current_page, catalogRuntimeState.total_pages);
    renderFilterChipStates();
    renderResetFiltersButtonState();

    initCatalogFiltersModal();
    initCardTabs();
    initLoadMore();
    initScrollToTopButton();
    initCatalogFilterDragTrack();
    initResetFiltersButton();

    await restoreCatalogIfNeeded();
    initCatalogStatePersistence();
}

document.addEventListener("DOMContentLoaded", () => {
    bootstrapCatalogPage().catch((error) => {
        console.error("Ошибка инициализации каталога:", error);
    });
});
