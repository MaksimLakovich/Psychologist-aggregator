import {
    clearCatalogState,
    consumeCatalogRestorePending,
    readCatalogState,
    toNonNegativeInt,
    toPositiveInt,
    writeCatalogState,
} from "./catalog_state.js";
import {
    catalogRuntimeState,
    getLoadMoreButton,
    normalizeCatalogFilters,
} from "./catalog_page_runtime.js";

/**
 * Restore-flow каталога.
 *
 * Этот модуль отвечает только за:
 * - запись текущего списка в sessionStorage;
 * - восстановление списка и позиции после возврата из detail;
 * - привязку кликов по ссылкам в detail.
 */

// Сохраняет текущее состояние каталога в sessionStorage.
// Это временная резервная копия для сценария возврата из detail.
export function persistCatalogState(extraState = {}) {
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

// Восстанавливает позицию прокрутки после возврата из detail.
// Сначала пробуем вернуться к конкретной карточке, а если не получилось, используем сохраненную координату прокрутки.
export function restoreCatalogScrollPosition(savedState) {
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

// Сохраняет состояние каталога перед переходом в detail.
// Это нужно, чтобы потом можно было вернуть пользователя на тот же набор карточек и к той же позиции.
export function initCatalogStatePersistence() {
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
export async function restoreCatalogIfNeeded({
    requestCatalogData,
    applyCatalogResponse,
} = {}) {
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
