import {
    catalogRuntimeState,
    normalizeCatalogFilters,
    resolveCatalogFilterEndpoint,
} from "./catalog_page_runtime.js";

/**
 * API-слой каталога.
 *
 * Его задача:
 * - собирать HTTP-запрос к backend в одном месте;
 * - давать page-слою единый метод для preview-count, фильтрации, догрузки и restore-flow.
 */

// Собирает заголовки для POST-запросов каталога.
export function buildCatalogRequestHeaders() {
    return {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": window.CSRF_TOKEN || "",
    };
}

// Делает AJAX-запрос к backend и возвращает JSON-ответ каталога.
// Один и тот же endpoint используем для preview-count, применения фильтров, догрузки карточек и восстановления каталога после detail.
export async function requestCatalogData({
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
