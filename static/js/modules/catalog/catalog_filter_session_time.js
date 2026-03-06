import { initToggleGroup } from "../toggle_group_single_choice.js";
import { initTimeSlotsPicker } from "../time_slots_picker.js";

/**
 * Фильтр каталога "Время сессии".
 *
 * Бизнес-задача этого файла:
 * - показать пользователю выбор между режимами "Любое" и "Конкретное";
 * - при режиме "Конкретное" показать доменные временные слоты на ближайшие 7 дней;
 * - передать странице каталога готовые функции для preview-count, применения фильтра и подсветки кнопки фильтра.
 */

export const CATALOG_SESSION_TIME_FILTER_KEY = "session_time";
export const CATALOG_SESSION_TIME_FILTER_NAME = "Время сессии";

// Приводит режим фильтра "Время сессии" к допустимому состоянию каталога.
// Если пришло некорректное значение, возвращаем "any", чтобы каталог работал без дополнительного ограничения.
export function normalizeCatalogSessionTimeMode(rawValue) {
    return rawValue === "specific" ? "specific" : "any";
}

// Возвращает поясняющий текст для текущего режима фильтра "Время сессии".
// Это нужно, чтобы одна и та же бизнес-формулировка использовалась и при первой отрисовке модалки, и при переключении режима внутри нее.
function resolveCatalogSessionTimeHelperText(sessionTimeMode) {
    return sessionTimeMode === "specific"
        ? "Будут показаны специалисты, к которым можно записаться в указанное вами день и время"
        : "Если оставить режим \"Любое\", каталог не будет дополнительно фильтроваться по времени";
}

// Приводит выбранные доменные слоты к чистому и безопасному виду.
// Простыми словами: оставляем только валидные ISO-значения datetime, убираем дубли и получаем предсказуемый набор для каталога и backend.
export function normalizeCatalogSelectedSessionSlots(rawValues) {
    if (!Array.isArray(rawValues)) return [];

    const normalizedSlots = [];
    const seenSlots = new Set();

    rawValues.forEach((rawValue) => {
        if (typeof rawValue !== "string" || !rawValue.trim()) return;

        const normalizedValue = rawValue.trim();
        const timestamp = Date.parse(normalizedValue);
        if (Number.isNaN(timestamp) || seenSlots.has(normalizedValue)) return;

        seenSlots.add(normalizedValue);
        normalizedSlots.push(normalizedValue);
    });

    return normalizedSlots;
}

// Проверяет, применен ли сейчас фильтр "Время сессии" в каталоге.
// Если функция возвращает true, страница понимает, что кнопка фильтра "Время сессии" должна подсветиться как активная.
export function isCatalogSessionTimeFilterActive(filters) {
    return normalizeCatalogSessionTimeMode(filters?.session_time_mode) === "specific"
        && normalizeCatalogSelectedSessionSlots(filters?.selected_session_slots).length > 0;
}

// Читает текущий режим фильтра прямо из открытой модалки.
// Это нужно, чтобы страница понимала, должен ли каталог работать в режиме "Любое" или "Конкретное".
export function getCatalogSessionTimeModalMode() {
    const hiddenInput = document.getElementById("catalog-session-time-mode-input");
    return normalizeCatalogSessionTimeMode(hiddenInput ? hiddenInput.value : "any");
}

// Читает текущие выбранные слоты прямо из открытой модалки.
// Это нужно и для применения фильтра, и для предварительного подсчета количества найденных специалистов.
export function getCatalogSessionTimeModalSelectedSlots() {
    const slotInputs = document.querySelectorAll("#ts-hidden-inputs input");
    return normalizeCatalogSelectedSessionSlots(
        Array.from(slotInputs).map((input) => input.value),
    );
}

// Собирает HTML содержимого модалки фильтра "Время сессии".
// Простыми словами: рисует две кнопки выбора режима и контейнер для уже существующего UI доменных слотов.
export function buildCatalogSessionTimeModalHtml({
    catalogRuntimeState,
}) {
    const sessionTimeMode = normalizeCatalogSessionTimeMode(catalogRuntimeState.filters.session_time_mode);
    const slotsWrapperClass = sessionTimeMode === "specific" ? "mt-4 rounded-2xl bg-gray-50" : "hidden mt-4 rounded-2xl bg-gray-50";
    const helperText = resolveCatalogSessionTimeHelperText(sessionTimeMode);

    return `
        <div class="space-y-4">
            <p class="text-sm pb-4 text-gray-500 leading-relaxed">
                Выберите, нужно ли учитывать конкретное время сессии при фильтрации каталога
            </p>

            <div class="grid grid-cols-2 gap-3 max-w-md">
                <button id="catalog-session-time-any-btn" type="button" class="px-4 py-2 rounded-lg border text-lg font-medium">
                    Любое
                </button>
                <button id="catalog-session-time-specific-btn" type="button" class="px-4 py-2 rounded-lg border text-lg font-medium">
                    Конкретное
                </button>
            </div>

            <input
                id="catalog-session-time-mode-input"
                type="hidden"
                value="${sessionTimeMode}"
            >

            <div
                id="catalog-time-slots-wrapper"
                class="${slotsWrapperClass}"
            >
                <div
                    id="ts-days-row"
                    class="flex flex-wrap justify-center gap-4 py-6"
                    data-btn-class="w-16 h-16 flex flex-col items-center justify-center rounded-full border text-sm text-indigo-600 font-medium"
                ></div>

                <div class="mt-4">
                    <div
                        id="ts-slots-grid"
                        class="grid grid-cols-4 sm:grid-cols-4 gap-2"
                        data-btn-class="px-5 py-3 w-auto justify-self-center rounded-full border text-sm font-medium"
                    ></div>

                    <div id="ts-hidden-inputs" class="hidden"></div>
                </div>

            </div>

            <p id="catalog-session-time-helper-text" class="text-xs text-gray-400">
                ${helperText}
            </p>
        </div>
    `;
}

// Собирает временное состояние фильтров только для preview-count в кнопке "Показать результаты".
// Простыми словами: пользователь еще не применил фильтр к каталогу, но мы уже можем посчитать, сколько специалистов будет найдено при текущем выборе режима и слотов.
export function buildCatalogSessionTimeTentativeFilters({
    catalogRuntimeState,
    normalizeCatalogFilters,
}) {
    return normalizeCatalogFilters({
        ...catalogRuntimeState.filters,
        session_time_mode: getCatalogSessionTimeModalMode(),
        selected_session_slots: getCatalogSessionTimeModalSelectedSlots(),
    });
}

// Рисует модалку фильтра "Время сессии" и подключает ее поведение.
// Бизнес-смысл: дать пользователю выбрать режим "Любое/Конкретное", а при необходимости переиспользовать уже готовый UI доменных временных слотов.
export function renderCatalogSessionTimeModal({
    modalContent,
    catalogRuntimeState,
    schedulePreviewRefresh,
    domainSlotsEndpoint,
}) {
    const initialSelectedSlots = normalizeCatalogSelectedSessionSlots(
        catalogRuntimeState.filters.selected_session_slots,
    );

    modalContent.innerHTML = buildCatalogSessionTimeModalHtml({
        catalogRuntimeState,
    });

    initToggleGroup({
        firstBtn: "#catalog-session-time-any-btn",
        secondBtn: "#catalog-session-time-specific-btn",
        valFirst: "any",
        valSecond: "specific",
        blockToToggleSelector: "#catalog-time-slots-wrapper",
        initialValue: normalizeCatalogSessionTimeMode(catalogRuntimeState.filters.session_time_mode),
        hiddenInputSelector: "#catalog-session-time-mode-input",
        showBlockWhen: "second",
    });

    const anyButton = document.getElementById("catalog-session-time-any-btn");
    const specificButton = document.getElementById("catalog-session-time-specific-btn");
    const slotsWrapper = document.getElementById("catalog-time-slots-wrapper");
    const helperText = document.getElementById("catalog-session-time-helper-text");

    // Синхронизирует UI открытой модалки с текущим режимом "Любое/Конкретное".
    // Простыми словами: сразу переключает видимость блока слотов и поясняющий текст, не дожидаясь повторного открытия модалки.
    function syncSessionTimeModeUi() {
        const currentMode = getCatalogSessionTimeModalMode();
        const isSpecificMode = currentMode === "specific";

        if (slotsWrapper) {
            slotsWrapper.classList.toggle("hidden", !isSpecificMode);
        }

        if (helperText) {
            helperText.textContent = resolveCatalogSessionTimeHelperText(currentMode);
        }
    }

    function initSlotsPickerIfNeeded() {
        if (!slotsWrapper || slotsWrapper.dataset.initialized === "true" || !domainSlotsEndpoint) {
            return;
        }

        initTimeSlotsPicker({
            containerSelector: "#catalog-time-slots-wrapper",
            apiUrl: domainSlotsEndpoint,
            initialSelectedSlots,
        });

        slotsWrapper.dataset.initialized = "true";
        slotsWrapper.addEventListener("preferred_slots:changed", () => {
            schedulePreviewRefresh();
        });
    }

    if (normalizeCatalogSessionTimeMode(catalogRuntimeState.filters.session_time_mode) === "specific") {
        initSlotsPickerIfNeeded();
    }

    syncSessionTimeModeUi();

    if (anyButton) {
        anyButton.addEventListener("click", () => {
            window.requestAnimationFrame(() => {
                syncSessionTimeModeUi();
                schedulePreviewRefresh();
            });
        });
    }

    if (specificButton) {
        specificButton.addEventListener("click", () => {
            initSlotsPickerIfNeeded();
            window.requestAnimationFrame(() => {
                syncSessionTimeModeUi();
                schedulePreviewRefresh();
            });
        });
    }
}
