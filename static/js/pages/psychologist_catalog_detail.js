import {
    readCatalogState,
    toNonNegativeInt,
    toPositiveInt,
} from "../modules/catalog_state.js";

/**
 * Логика страницы детального профиля психолога.
 *
 * Главная задача:
 * - показать "красивый" URL профиля без длинных query-параметров;
 * - при нажатии "Назад в каталог" вернуть клиента туда, где он был в каталоге.
 *
 * Как выбираем способ возврата:
 * 1) сначала пробуем history.back() (обычно это самый точный возврат);
 * 2) если history-back не подходит, используем fallback URL из sessionStorage.
 */

/**
 * Регулярка, которая проверяет путь каталога.
 *
 * Поддерживает оба варианта:
 * - /psychologist_catalog
 * - /psychologist_catalog/
 *
 * Зачем это вообще нужно:
 * - это защитный барьер перед вызовом history.back();
 * - мы явно проверяем, что пользователь действительно пришел в detail из каталога.
 *
 * Если пользователь попал в detail не из каталога (например, открыл прямую ссылку),
 * history.back() может вернуть не туда, куда ожидаем.
 * В таком случае включается fallback-ветка с восстановлением по sessionStorage.
 *
 * По сути это "страховка на будущее": стоимость почти нулевая, а риск странной навигации ниже.
 */
const CATALOG_PATH_PATTERN = /^\/psychologist_catalog\/?$/;

/**
 * Приводит anchor к безопасному формату slug.
 *
 * Пример:
 * - "anna-ivanova" -> "anna-ivanova" (валидно)
 * - " Anna-Ivanova " -> "anna-ivanova" (нормализация)
 * - "anna_ivanova" -> null (символ "_" не разрешен)
 */
function normalizeAnchor(rawAnchor) {
    if (!rawAnchor || typeof rawAnchor !== "string") return null;

    const normalized = rawAnchor.trim().toLowerCase();
    if (!normalized) return null;

    if (!/^[a-z0-9-]+$/.test(normalized)) return null;
    return normalized;
}

/**
 * Собирает URL каталога для fallback-возврата.
 *
 * Что восстанавливаем:
 * - layout (menu/sidebar);
 * - page + restore (если пользователь был дальше первой страницы);
 * - order_key (чтобы порядок карточек сохранился);
 * - hash-якорь на выбранную карточку.
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
 * Проверяет, что клиент пришел именно из каталога в этой же вкладке.
 *
 * Это важно для history.back():
 * - если реферер действительно каталог, возврат обычно идеальный;
 * - если реферер другой, лучше использовать fallback URL.
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
 * Подключает поведение кнопки "Назад в каталог".
 *
 * Пошагово:
 * 1) если в storage есть состояние, сразу ставим fallback href;
 * 2) на клик пытаемся сделать history.back();
 * 3) если history.back() использовать нельзя — переходим на fallback URL;
 * 4) если storage пуст, оставляем обычное поведение ссылки (server fallback).
 *
 * Почему так:
 * - history.back() дает лучший UX (точная позиция и нативное поведение браузера);
 * - fallback нужен как резерв, чтобы поведение оставалось предсказуемым даже в нетипичных входах в detail.
 */
function initCatalogBackLink() {
    const backLink = document.querySelector("[data-catalog-back-link]");
    if (!backLink) return;

    const catalogBaseUrl = backLink.dataset.catalogUrl || "/psychologist_catalog/";
    const stateFromStorage = readCatalogState();

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
            return;
        }

        event.preventDefault();
        window.location.href = buildCatalogRestoreUrl(catalogBaseUrl, fallbackState);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initCatalogBackLink();
});
