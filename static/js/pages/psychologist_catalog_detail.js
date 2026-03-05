import {
    markCatalogRestorePending,
    readCatalogState,
} from "../modules/catalog_state.js";
import { initGlobalTextToggleHandlers } from "../modules/detail_card/detail_card_content_toggle.js";
import { initDetailCardModals } from "../modules/detail_card/detail_card_modals.js";
import { renderPsychologistCard } from "../modules/detail_card/detail_card_render.js";
import { initSessionChoiceState } from "../modules/detail_card/detail_card_session_choice.js";
import { initStickyHeaderBehavior } from "../modules/detail_card/detail_card_sticky_companion.js";

/**
 * Логика страницы детального профиля психолога из каталога.
 *
 * Главная задача:
 * - по кнопке "Назад в каталог" вернуть клиента туда, где он был в каталоге;
 * - при этом не тащить длинные фильтр-параметры в URL detail-страницы;
 * - отрисовать карточку тем же runtime, что и на странице выбора психолога.
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
    // На странице может быть несколько кнопок "Назад в каталог" (вверху и внизу).
    // Важно, чтобы обе работали одинаково и не сбрасывали фильтры.
    const backLinks = Array.from(document.querySelectorAll("[data-catalog-back-link]"));
    if (!backLinks.length) return;

    const stateFromStorage = readCatalogState();

    backLinks.forEach((backLink) => {
        const catalogBaseUrl = backLink.dataset.catalogUrl || "/psychologist_catalog/";
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

function readDetailPsychologistPayload() {
    const payloadNode = document.getElementById("catalog-detail-psychologist-data");
    if (!payloadNode) return null;

    try {
        const parsed = JSON.parse(payloadNode.textContent || "{}");
        if (!parsed || typeof parsed !== "object") return null;
        return parsed;
    } catch (error) {
        return null;
    }
}

function resolveCatalogConsultationType() {
    const state = readCatalogState();
    const value = state?.filters?.consultation_type;
    return value === "individual" || value === "couple" ? value : null;
}

function initCatalogDetailCard() {
    const psPayload = readDetailPsychologistPayload();
    if (!psPayload) return;

    const consultationType = resolveCatalogConsultationType();

    const psychologists = [
        {
            ...psPayload,
            // Для переиспользования существующего шаблона карточки в runtime
            // заполняем matched_topics полным списком тем из БД психолога.
            matched_topics: psPayload.topics || [],
        },
    ];

    initGlobalTextToggleHandlers();
    initDetailCardModals({
        getPsychologistsList: () => psychologists,
    });
    initSessionChoiceState();

    renderPsychologistCard(psychologists[0], {
        mode: "catalog-detail",
        consultationType,
        topicsField: "topics",
        topicsTitle: "С чем работает",
        // В каталоге пока нет перехода в общий payment-flow подбора.
        // Поэтому кнопка становится активной после выбора слота, но остается заглушкой без submit.
        chooseSessionButtonType: "button",
        // Нижняя кнопка "Назад" не нужна: используем только верхний "Назад в каталог".
        showBottomBackButton: false,
    });

    initStickyHeaderBehavior();
}

document.addEventListener("DOMContentLoaded", () => {
    warmCatalogStateTtlGuard();
    initCatalogBackLink();
    initCatalogDetailCard();
});
