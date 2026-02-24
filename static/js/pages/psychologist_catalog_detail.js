/**
 * Страница детального профиля психолога из каталога.
 *
 * Основная задача:
 * 1) сохранить "красивый" URL детальной страницы без query-параметров;
 * 2) по кнопке "Назад в каталог" вернуть пользователя в прежнее состояние каталога.
 *
 * Приоритет возврата:
 *   - сначала используем history.back() (идеально восстанавливает scroll и DOM-состояние);
 *   - если history-back невозможен, используем fallback URL на основе sessionStorage.
 */

const CATALOG_STATE_STORAGE_KEY = "psychologist_catalog_state_v1";
const CATALOG_STATE_TTL_MS = 1000 * 60 * 60 * 6; // 6 часов

function toPositiveInt(value, fallback = null) {
    const parsed = Number.parseInt(String(value), 10);
    if (Number.isInteger(parsed) && parsed > 0) {
        return parsed;
    }
    return fallback;
}

function readCatalogState() {
    try {
        const rawState = window.sessionStorage.getItem(CATALOG_STATE_STORAGE_KEY);
        if (!rawState) return null;

        const parsedState = JSON.parse(rawState);
        if (!parsedState || typeof parsedState !== "object") return null;

        const updatedAt = toPositiveInt(parsedState.updated_at, null);
        if (updatedAt && Date.now() - updatedAt > CATALOG_STATE_TTL_MS) {
            window.sessionStorage.removeItem(CATALOG_STATE_STORAGE_KEY);
            return null;
        }

        return parsedState;
    } catch (error) {
        return null;
    }
}

function normalizeAnchor(rawAnchor) {
    if (!rawAnchor || typeof rawAnchor !== "string") return null;

    const normalized = rawAnchor.trim().toLowerCase();
    if (!normalized) return null;

    // Такой же whitelist, как на сервере: slug-символы.
    if (!/^[a-z0-9-]+$/.test(normalized)) return null;
    return normalized;
}

function buildCatalogRestoreUrl(catalogBaseUrl, catalogState) {
    const url = new URL(catalogBaseUrl, window.location.origin);
    const params = new URLSearchParams();

    const layoutMode = catalogState.layout_mode === "sidebar" ? "sidebar" : "menu";
    params.set("layout", layoutMode);

    const currentPage = toPositiveInt(catalogState.current_page, 1);
    if (currentPage > 1) {
        params.set("page", String(currentPage));
        params.set("restore", "1");
    }

    const orderKey = toPositiveInt(catalogState.order_key, null);
    if (orderKey) {
        params.set("order_key", String(orderKey));
    }

    url.search = params.toString();

    const anchor = normalizeAnchor(catalogState.anchor);
    if (anchor) {
        url.hash = `psychologist-card-${anchor}`;
    }

    return url.toString();
}

function cameFromCatalogInSameTab() {
    try {
        if (!document.referrer) return false;

        const referrerUrl = new URL(document.referrer);
        if (referrerUrl.origin !== window.location.origin) return false;

        return referrerUrl.pathname.startsWith("/psychologist_catalog/");
    } catch (error) {
        return false;
    }
}

function initCatalogBackLink() {
    const backLink = document.querySelector("[data-catalog-back-link]");
    if (!backLink) return;

    const catalogBaseUrl = backLink.dataset.catalogUrl || "/psychologist_catalog/";
    const stateFromStorage = readCatalogState();

    // Для fallback-сценария сразу подставляем рассчитанный href.
    if (stateFromStorage) {
        backLink.setAttribute("href", buildCatalogRestoreUrl(catalogBaseUrl, stateFromStorage));
    }

    backLink.addEventListener("click", (event) => {
        // Базовый сценарий: пользователь пришел из каталога этой же вкладки.
        // history.back() вернет точно на ту же позицию и с тем же состоянием DOM.
        if (cameFromCatalogInSameTab() && window.history.length > 1) {
            event.preventDefault();
            window.history.back();
            return;
        }

        const fallbackState = readCatalogState();
        if (!fallbackState) {
            return;
        }

        event.preventDefault();
        window.location.href = buildCatalogRestoreUrl(catalogBaseUrl, fallbackState);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initCatalogBackLink();
});
