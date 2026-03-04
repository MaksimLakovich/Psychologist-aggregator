import {
    buildCatalogAgeTentativeFilters,
    CATALOG_AGE_FILTER_KEY,
    CATALOG_AGE_FILTER_NAME,
    getCatalogAgeModalValues,
    isCatalogAgeFilterActive,
    renderCatalogAgeModal,
} from "./catalog_filter_age.js";
import {
    buildCatalogExperienceTentativeFilters,
    CATALOG_EXPERIENCE_FILTER_KEY,
    CATALOG_EXPERIENCE_FILTER_NAME,
    getCatalogExperienceModalValues,
    isCatalogExperienceFilterActive,
    renderCatalogExperienceModal,
} from "./catalog_filter_experience.js";
import {
    buildCatalogGenderTentativeFilters,
    CATALOG_GENDER_FILTER_KEY,
    CATALOG_GENDER_FILTER_NAME,
    getCatalogGenderModalValue,
    isCatalogGenderFilterActive,
    renderCatalogGenderModal,
} from "./catalog_filter_gender.js";
import {
    buildCatalogMethodsTentativeFilters,
    CATALOG_METHODS_FILTER_KEY,
    CATALOG_METHODS_FILTER_NAME,
    getCatalogMethodsModalValues,
    isCatalogMethodsFilterActive,
    renderCatalogMethodsModal,
} from "./catalog_filter_methods.js";
import {
    buildCatalogPriceTentativeFilters,
    CATALOG_PRICE_FILTER_KEY,
    CATALOG_PRICE_FILTER_NAME,
    getCatalogPriceModalValues,
    isCatalogPriceFilterActive,
    renderCatalogPriceModal,
} from "./catalog_filter_price.js";
import {
    buildCatalogSessionTimeTentativeFilters,
    CATALOG_SESSION_TIME_FILTER_KEY,
    CATALOG_SESSION_TIME_FILTER_NAME,
    getCatalogSessionTimeModalMode,
    getCatalogSessionTimeModalSelectedSlots,
    isCatalogSessionTimeFilterActive,
    renderCatalogSessionTimeModal,
} from "./catalog_filter_session_time.js";
import {
    buildCatalogTopicTypeTentativeFilters,
    CATALOG_TOPIC_TYPE_FILTER_KEY,
    CATALOG_TOPIC_TYPE_FILTER_NAME,
    getCatalogTopicTypeModalValue,
    isCatalogTopicTypeFilterActive,
    renderCatalogTopicTypeModal,
} from "./catalog_filter_topic_type.js";
import {
    buildCatalogTopicsTentativeFilters,
    CATALOG_TOPICS_FILTER_KEY,
    CATALOG_TOPICS_FILTER_NAME,
    getCatalogTopicsModalValues,
    isCatalogTopicsFilterActive,
    renderCatalogTopicsModal,
} from "./catalog_filter_topics.js";
import {
    catalogRuntimeState,
    escapeHtml,
    normalizeCatalogFilters,
    readJsonScript,
    resolveCatalogDomainSlotsEndpoint,
} from "./catalog_page_runtime.js";

/**
 * Единый реестр фильтров каталога.
 *
 * Он одновременно описывает:
 * - порядок показа filter-chip на странице;
 * - имя и технический ключ фильтра;
 * - точки входа для рендера модалки и чтения данных из нее.
 */

export const CATALOG_FILTER_CHIP_ORDER = [
    CATALOG_TOPIC_TYPE_FILTER_KEY,
    CATALOG_TOPICS_FILTER_KEY,
    CATALOG_AGE_FILTER_KEY,
    CATALOG_METHODS_FILTER_KEY,
    CATALOG_GENDER_FILTER_KEY,
    CATALOG_PRICE_FILTER_KEY,
    CATALOG_EXPERIENCE_FILTER_KEY,
    CATALOG_SESSION_TIME_FILTER_KEY,
];

export const CATALOG_FILTER_REGISTRY = {
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

// Возвращает конфиг поддерживаемого фильтра по его ключу.
export function getCatalogFilterConfig(filterKey = "") {
    return filterKey ? CATALOG_FILTER_REGISTRY[filterKey] || null : null;
}

// Возвращает конфиги фильтров в том порядке, в котором они должны быть показаны пользователю.
export function getCatalogFilterChipConfigs() {
    return CATALOG_FILTER_CHIP_ORDER
        .map((filterKey) => getCatalogFilterConfig(filterKey))
        .filter(Boolean);
}

// Рендерит filter-chip прямо из registry.
// Так шаблон больше не дублирует вручную ключи и названия фильтров, а берет их из одного источника правды.
export function renderCatalogFilterChips() {
    const chipsContainer = document.getElementById("catalog-filter-scroll-area");
    if (!chipsContainer) return;

    const filterIconSrc = chipsContainer.dataset.filterIconSrc || "";
    const filterIconMarkup = filterIconSrc
        ? `<img src="${escapeHtml(filterIconSrc)}" alt="filter" class="w-5 h-5">`
        : "";

    chipsContainer.innerHTML = getCatalogFilterChipConfigs().map((filterConfig) => `
        <button
            type="button"
            data-filter-chip
            data-filter-key="${escapeHtml(filterConfig.key)}"
            class="inline-flex gap-1 flex-shrink-0 px-3 py-3 bg-slate-200/40 border border-slate-100 rounded-2xl text-sm font-bold text-slate-600
            hover:border-slate-100 hover:text-indigo-600 hover:bg-slate-50 transition-all shadow-sm"
        >
            ${escapeHtml(filterConfig.name)}
            ${filterIconMarkup}
        </button>
    `).join("");
}
