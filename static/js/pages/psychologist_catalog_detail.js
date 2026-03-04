import {
    markCatalogRestorePending,
    readCatalogState,
} from "../modules/catalog_state.js";

/**
 * Логика страницы детального профиля психолога.
 *
 * Главная задача:
 * - по кнопке "Назад в каталог" вернуть клиента туда, где он был в каталоге;
 * - при этом не тащить длинные фильтр-параметры в URL detail-страницы.
 *
 * Как работает возврат:
 * 1) если браузерный history.back() действительно ведет в каталог, используем его;
 * 2) если history.back() не подходит, включаем fallback:
 *    - ставим одноразовый флаг "нужно восстановить каталог";
 *    - переходим на чистый URL каталога;
 *    - каталог сам восстановит фильтры и позицию по sessionStorage.
 */

// Проверяет, что клиент пришел именно из каталога в этой же вкладке.
// Если это так, history.back() обычно дает самый точный возврат.
const CATALOG_PATH_PATTERN = /^\/psychologist_catalog\/?$/;

// Собирает "чистый" URL каталога для fallback-возврата.
// Здесь сознательно не передаем page/order_key/filters в query-параметрах.
// Все эти данные каталог восстановит сам через AJAX по sessionStorage.
function buildCatalogFallbackUrl(catalogBaseUrl, catalogState) {
    const url = new URL(catalogBaseUrl, window.location.origin);
    const layoutMode = catalogState?.layout_mode === "sidebar" ? "sidebar" : "menu";
    url.searchParams.set("layout", layoutMode);
    return url.toString();
}

// Проверяет, что пользователь пришел в detail именно из каталога в этой вкладке.
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

// Подключает поведение кнопки "Назад в каталог".
// Важный нюанс:
// - если fallback-сценарий срабатывает после долгого пути пользователя,
//   мы не должны пытаться восстановить каталог без сохраненного состояния;
// - поэтому restore-флаг ставим только тогда, когда состояние реально есть.
function initCatalogBackLink() {
    const backLink = document.querySelector("[data-catalog-back-link]");
    if (!backLink) return;

    const catalogBaseUrl = backLink.dataset.catalogUrl || "/psychologist_catalog/";
    const stateFromStorage = readCatalogState();
    if (stateFromStorage) {
        backLink.setAttribute("href", buildCatalogFallbackUrl(catalogBaseUrl, stateFromStorage));
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
        markCatalogRestorePending();
        window.location.href = buildCatalogFallbackUrl(catalogBaseUrl, fallbackState);
    });
}

// Небольшой защитный прогрев sessionStorage-state.
// Зачем это вообще нужно:
// - если браузер восстановил очень старую вкладку detail,
//   мы лишний раз читаем state и даем catalog_state.js шанс вычистить просроченную запись по TTL.
// - новых данных здесь не создаем и ничего не меняем.
function warmCatalogStateTtlGuard() {
    // Сам факт чтения уже запускает TTL-проверку внутри readCatalogState().
    readCatalogState();
}

document.addEventListener("DOMContentLoaded", () => {
    warmCatalogStateTtlGuard();
    initCatalogBackLink();
});
