/**
 * Страница детального профиля психолога из каталога.
 *
 * Цель файла:
 * 1) Оставить красивый URL детальной страницы без длинных query-параметров.
 * 2) По кнопке "Назад в каталог" восстановить предыдущее состояние каталога.
 *
 * Логика возврата:
 * - приоритет №1: history.back() (возвращает максимально точно, включая scroll/DOM);
 * - fallback: URL, собранный из состояния в sessionStorage.
 */

const CATALOG_STATE_STORAGE_KEY = "psychologist_catalog_state_v1";
const CATALOG_STATE_TTL_MS = 1000 * 60 * 60 * 6; // 6 часов
const CATALOG_PATH_PATTERN = /^\/psychologist_catalog\/?$/;

/**
 * Преобразует значение в целое число > 0.
 * Используем для page и timestamp.
 */
function toPositiveInt(value, fallback = null) {
    const parsed = Number.parseInt(String(value), 10);
    if (Number.isInteger(parsed) && parsed > 0) {
        return parsed;
    }
    return fallback;
}

/**
 * Преобразует значение в целое число >= 0.
 * Используем для order_key: значение 0 считается валидным.
 */
function toNonNegativeInt(value, fallback = null) {
    const parsed = Number.parseInt(String(value), 10);
    if (Number.isInteger(parsed) && parsed >= 0) {
        return parsed;
    }
    return fallback;
}

/**
 * Читает состояние каталога из sessionStorage.
 *
 * Возвращает:
 * - валидный объект состояния, если он есть и не просрочен;
 * - null в остальных случаях.
 */
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

/**
 * Нормализует якорь карточки (slug) для безопасного добавления в hash URL.
 * Разрешаем только [a-z0-9-], как и на стороне сервера.
 */
function normalizeAnchor(rawAnchor) {
    if (!rawAnchor || typeof rawAnchor !== "string") return null;

    const normalized = rawAnchor.trim().toLowerCase();
    if (!normalized) return null;

    if (!/^[a-z0-9-]+$/.test(normalized)) return null;
    return normalized;
}

/**
 * Собирает fallback URL каталога на основе состояния из storage.
 *
 * Что восстанавливает:
 * - layout (`sidebar/menu`);
 * - page + restore (если пользователь был дальше первой страницы);
 * - order_key (чтобы порядок карточек не менялся);
 * - hash-якорь на конкретную карточку.
 */
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

    const orderKey = toNonNegativeInt(catalogState.order_key, null);
    if (orderKey !== null) {
        params.set("order_key", String(orderKey));
    }

    url.search = params.toString();

    const anchor = normalizeAnchor(catalogState.anchor);
    if (anchor) {
        url.hash = `psychologist-card-${anchor}`;
    }

    return url.toString();
}

/**
 * Проверяет, что пользователь пришел именно из каталога в этой же вкладке.
 * Это сигнал, что history.back() обычно сработает оптимально.
 */
function cameFromCatalogInSameTab() {
    try {
        if (!document.referrer) return false;

        const referrerUrl = new URL(document.referrer);
        if (referrerUrl.origin !== window.location.origin) return false;

        return CATALOG_PATH_PATTERN.test(referrerUrl.pathname);
    } catch (error) {
        return false;
    }
}

/**
 * Инициализирует кнопку "Назад в каталог".
 *
 * Алгоритм:
 * 1) Если есть состояние в storage — подставляем fallback href.
 * 2) На клик пробуем history.back() (если пришли из каталога и есть history).
 * 3) Если history.back() не подходит — уходим на URL, собранный из storage.
 * 4) Если storage пуст — оставляем поведение обычной ссылки (server fallback href).
 */
function initCatalogBackLink() {
    const backLink = document.querySelector("[data-catalog-back-link]");
    if (!backLink) return;

    const catalogBaseUrl = backLink.dataset.catalogUrl || "/psychologist_catalog/";
    const stateFromStorage = readCatalogState();

    // Если storage есть, заранее подготавливаем fallback URL.
    if (stateFromStorage) {
        backLink.setAttribute("href", buildCatalogRestoreUrl(catalogBaseUrl, stateFromStorage));
    }

    backLink.addEventListener("click", (event) => {
        if (cameFromCatalogInSameTab() && window.history.length > 1) {
            event.preventDefault();
            window.history.back();
            return;
        }

        const fallbackState = readCatalogState();
        if (!fallbackState) {
            // Storage нет: пусть сработает обычная ссылка (server fallback).
            return;
        }

        event.preventDefault();
        window.location.href = buildCatalogRestoreUrl(catalogBaseUrl, fallbackState);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initCatalogBackLink();
});
