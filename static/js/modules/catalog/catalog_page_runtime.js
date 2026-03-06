import {
    filterCatalogTopicIdsByConsultationType,
    normalizeCatalogTopicIds,
} from "./catalog_filter_topics.js";
import {
    normalizeCatalogTopicType,
} from "./catalog_filter_topic_type.js";
import {
    normalizeCatalogMethodIds,
} from "./catalog_filter_methods.js";
import {
    normalizeCatalogGender,
} from "./catalog_filter_gender.js";
import {
    normalizeCatalogPriceFilters,
} from "./catalog_filter_price.js";
import {
    normalizeCatalogAgeRange,
} from "./catalog_filter_age.js";
import {
    normalizeCatalogExperienceRange,
} from "./catalog_filter_experience.js";
import {
    normalizeCatalogSelectedSessionSlots,
    normalizeCatalogSessionTimeMode,
} from "./catalog_filter_session_time.js";
import {
    toNonNegativeInt,
    toPositiveInt,
} from "./catalog_state.js";

/**
 * Общее runtime-состояние страницы каталога.
 *
 * Здесь живут только данные и инфраструктурные helper-функции,
 * которые нужны сразу нескольким модулям страницы.
 */

export const APPLY_RESULTS_LABEL = "Показать результаты";
export const PREVIEW_RESULTS_LABEL = "Считаем результаты...";

// Временное состояние каталога для текущей вкладки браузера.
// Это не БД и не server session, а только рабочие данные текущего сценария пользователя.
export const catalogRuntimeState = {
    layout_mode: "menu",
    current_page: 1,
    total_pages: 0,
    order_key: null,
    anchor: null,
    scroll_y: 0,
    filters: {},
};

// Возвращает дефолтное состояние всех фильтров каталога.
// Это один общий источник правды для первого рендера страницы и для кнопки "Сбросить фильтры".
export function buildDefaultCatalogFilters() {
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
export function escapeHtml(value) {
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
export function readJsonScript(id, fallback) {
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
export function normalizeCatalogFilters(rawFilters = {}) {
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

// Возвращает кнопку "Показать еще".
// В ее data-атрибутах лежит часть стартового состояния каталога.
export function getLoadMoreButton() {
    return document.getElementById("catalog-load-more-btn");
}

// Возвращает AJAX-endpoint каталога.
export function resolveCatalogFilterEndpoint() {
    const loadMoreButton = getLoadMoreButton();
    return loadMoreButton?.dataset.filterEndpoint || "";
}

// Возвращает read-only endpoint доменных слотов для фильтра "Время сессии".
export function resolveCatalogDomainSlotsEndpoint() {
    const loadMoreButton = getLoadMoreButton();
    return loadMoreButton?.dataset.domainSlotsEndpoint || "";
}

// Считывает стартовое состояние каталога из data-атрибутов страницы.
export function hydrateRuntimeStateFromDom() {
    const loadMoreButton = getLoadMoreButton();
    if (!loadMoreButton) return;

    catalogRuntimeState.layout_mode = loadMoreButton.dataset.layout === "sidebar" ? "sidebar" : "menu";
    catalogRuntimeState.current_page = toPositiveInt(loadMoreButton.dataset.currentPage, 1);
    catalogRuntimeState.total_pages = toNonNegativeInt(loadMoreButton.dataset.totalPages, 0);
    catalogRuntimeState.order_key = toNonNegativeInt(loadMoreButton.dataset.randomOrderKey, null);
    catalogRuntimeState.filters = normalizeCatalogFilters(buildDefaultCatalogFilters());
}
