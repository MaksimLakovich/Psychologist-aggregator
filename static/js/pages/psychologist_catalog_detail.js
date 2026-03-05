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
 *
 * Почему это важно для бизнеса:
 * - клиент видит единый UX карточки на всех шагах продукта;
 * - возврат в каталог не ломает уже выбранные фильтры и не заставляет
 *   пользователя повторно настраивать поиск специалиста;
 * - страница detail остается "легкой" по URL, а состояние живет в sessionStorage.
 */

// Проверяет, что клиент пришел именно из каталога в этой же вкладке.
// Если это так, history.back() обычно дает самый точный возврат.
const CATALOG_PATH_PATTERN = /^\/psychologist_catalog\/?$/;

// Собирает "чистый" URL каталога для fallback-возврата.
// Здесь сознательно не передаем page/order_key/filters в query-параметрах.
// Все эти данные каталог восстановит сам через AJAX по sessionStorage.
function buildCatalogFallbackUrl(catalogBaseUrl, catalogState) {
    // Строим абсолютный URL, чтобы корректно работать при разных referrer-сценариях.
    const url = new URL(catalogBaseUrl, window.location.origin);
    // Жесткий fallback по layout защищает от битого/устаревшего состояния в storage.
    const layoutMode = catalogState?.layout_mode === "sidebar" ? "sidebar" : "menu";
    // Передаем только layout, а фильтры каталог восстановит из sessionStorage.
    url.searchParams.set("layout", layoutMode);
    return url.toString();
}

// Проверяет, что пользователь пришел в detail именно из каталога в этой вкладке.
function cameFromCatalogInSameTab() {
    try {
        // Если referrer отсутствует, значит "точный возврат назад" недоступен.
        if (!document.referrer) return false;

        const referrerUrl = new URL(document.referrer);
        // Возвращаться по history.back() безопасно только в пределах нашего домена.
        if (referrerUrl.origin !== window.location.origin) return false;

        // Дополнительно убеждаемся, что прошлый экран именно каталог.
        return CATALOG_PATH_PATTERN.test(referrerUrl.pathname);
    } catch (error) {
        // Любая ошибка парсинга referrer означает "не уверены" => используем fallback-сценарий.
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

    // Один раз читаем state, чтобы сразу проставить корректный href во все кнопки.
    // Это улучшает UX: даже "Открыть в новой вкладке" ведет по корректному fallback URL.
    const stateFromStorage = readCatalogState();

    backLinks.forEach((backLink) => {
        // Каждый линк может иметь свой base URL через data-атрибут (на будущее/переиспользование).
        const catalogBaseUrl = backLink.dataset.catalogUrl || "/psychologist_catalog/";
        if (stateFromStorage) {
            backLink.setAttribute("href", buildCatalogFallbackUrl(catalogBaseUrl, stateFromStorage));
        }

        backLink.addEventListener("click", (event) => {
            // При "чистом" переходе из каталога в этой вкладке history.back() дает
            // самый естественный для клиента эффект (сохраняется позиция скролла списка).
            if (cameFromCatalogInSameTab() && window.history.length > 1) {
                event.preventDefault();
                window.history.back();
                return;
            }

            // Если history-путь непредсказуем, включаем управляемый fallback.
            const fallbackState = readCatalogState();
            if (!fallbackState) {
                // Нет состояния => позволяем обычный переход по href.
                return;
            }

            // Ставим restore-флаг: каталог поймет, что нужно поднять фильтры/выдачу из storage.
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
    // Payload подготавливается сервером как json_script.
    // Это контракт "один психолог целиком", чтобы не делать лишний API-запрос на detail.
    const payloadNode = document.getElementById("catalog-detail-psychologist-data");
    if (!payloadNode) return null;

    try {
        const parsed = JSON.parse(payloadNode.textContent || "{}");
        // Защита от некорректной структуры payload.
        if (!parsed || typeof parsed !== "object") return null;
        return parsed;
    } catch (error) {
        // При битом JSON безопасно прекращаем рендер карточки.
        return null;
    }
}

function resolveCatalogConsultationType() {
    // В detail-карточке нужно показывать цену в контексте выбранного в каталоге фильтра
    // "Вид консультации", поэтому читаем его из сохраненного состояния каталога.
    const state = readCatalogState();
    const value = state?.filters?.consultation_type;
    // Поддерживаем только валидные бизнес-значения.
    return value === "individual" || value === "couple" ? value : null;
}

function initCatalogDetailCard() {
    // Если сервер не передал payload, не рендерим карточку (избегаем поломанного UI).
    const psPayload = readDetailPsychologistPayload();
    if (!psPayload) return;

    // Этот признак влияет на отображение цены (одна или две цены).
    const consultationType = resolveCatalogConsultationType();

    // Модалки detail-card ожидают список психологов (matching-формат).
    // В каталоге у нас один специалист, поэтому делаем массив из одного элемента.
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
    // На входе в detail-сценарий всегда сбрасываем выбранный слот,
    // чтобы клиент не унаследовал старое время от другого психолога/страницы.
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

    // Подключаем "липкий компаньон" для длинной карточки: фото + ключевые данные остаются в поле зрения.
    initStickyHeaderBehavior();
}

document.addEventListener("DOMContentLoaded", () => {
    // 1) Прогреваем state (TTL-cleanup), 2) настраиваем возврат в каталог, 3) рендерим карточку.
    warmCatalogStateTtlGuard();
    initCatalogBackLink();
    initCatalogDetailCard();
});
