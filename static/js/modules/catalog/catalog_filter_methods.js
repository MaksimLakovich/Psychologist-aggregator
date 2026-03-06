import { initCollapsibleList } from "../collapsible_methods_list.js";

/**
 * Фильтр каталога "Подход".
 *
 * Бизнес-задача этого файла:
 * - показать пользователю модалку со списком методов и подходов психолога;
 * - понять, какие методы пользователь выбрал для поиска психолога;На странице "Каталог" реализован фильтр "ВОЗРАСТ"
 * - передать странице каталога готовые функции для preview-count, применения фильтра и подсветки кнопки фильтра.
 */

export const CATALOG_METHODS_FILTER_KEY = "method_ids";
export const CATALOG_METHODS_FILTER_NAME = "Подход";

// Кешируем методы каталога, чтобы не читать один и тот же json_script много раз за жизнь страницы.
let cachedCatalogMethods = null;

// Читает с backend список методов для модалки фильтра "Подход".
// Простыми словами: именно отсюда берем все названия подходов, которые показываем пользователю в списке чекбоксов.
export function getCatalogMethods({ readJsonScript }) {
    if (cachedCatalogMethods !== null) {
        return cachedCatalogMethods;
    }

    const rawMethods = readJsonScript("catalog-methods-data", []);
    cachedCatalogMethods = Array.isArray(rawMethods) ? rawMethods : [];
    return cachedCatalogMethods;
}

// Приводит выбранные method-id к чистому и безопасному виду.
// Простыми словами: оставляем только корректные id методов, убираем дубли и получаем предсказуемый набор значений для каталога и backend.
export function normalizeCatalogMethodIds(rawValues) {
    if (!Array.isArray(rawValues)) return [];

    const normalizedMethodIds = [];
    const seenMethodIds = new Set();

    rawValues.forEach((rawValue) => {
        const parsedValue = Number.parseInt(String(rawValue), 10);
        if (!Number.isInteger(parsedValue) || parsedValue <= 0) return;

        const normalizedValue = String(parsedValue);
        if (seenMethodIds.has(normalizedValue)) return;

        seenMethodIds.add(normalizedValue);
        normalizedMethodIds.push(normalizedValue);
    });

    return normalizedMethodIds;
}

// Проверяет, применен ли сейчас фильтр "Подход" в каталоге.
// Если функция возвращает true, страница понимает, что кнопка фильтра "Подход" должна подсветиться как активная.
export function isCatalogMethodsFilterActive(filters) {
    return normalizeCatalogMethodIds(filters?.method_ids).length > 0;
}

// Читает из открытой модалки, какие методы пользователь отметил чекбоксами прямо сейчас.
// Это нужно и для применения фильтра, и для предварительного подсчета количества найденных специалистов.
export function getCatalogMethodsModalValues() {
    const checkboxes = document.querySelectorAll("#catalog-methods-grid .catalog-method-checkbox:checked");
    return normalizeCatalogMethodIds(Array.from(checkboxes).map((checkbox) => checkbox.value));
}

// Собирает HTML содержимого модалки фильтра "Подход".
// Простыми словами: превращает список методов из backend в удобный набор чекбоксов, который пользователь видит в интерфейсе.
export function buildCatalogMethodsModalHtml({ selectedMethodIds, escapeHtml, readJsonScript }) {
    const methods = getCatalogMethods({ readJsonScript });

    if (!methods.length) {
        return `
            <p class="text-sm text-gray-500 leading-relaxed">
                Методы пока не добавлены.
            </p>
        `;
    }

    const itemsHtml = methods.map((method) => `
        <label class="method-item flex items-center gap-3 p-1 rounded-md hover:bg-gray-50 transition">
            <input
                type="checkbox"
                value="${method.id}"
                class="catalog-method-checkbox w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                ${selectedMethodIds.includes(String(method.id)) ? "checked" : ""}
            >
            <span class="text-sm sm:text-base font-medium text-gray-900">${escapeHtml(method.name)}</span>
        </label>
    `).join("");

    return `
        <div class="space-y-4">
            <p class="text-sm text-gray-500 leading-relaxed">
                Выберите подходы и методы, которыми должен владеть психолог.
            </p>
            <div id="catalog-methods-grid" class="max-h-[28rem] overflow-y-auto pr-1 grid grid-cols-1 sm:grid-cols-2 gap-y-1">
                ${itemsHtml}
            </div>
            <button
                id="catalog-show-more-methods"
                type="button"
                class="hidden italic text-sm font-medium text-indigo-500 hover:text-indigo-900"
            >
                Ещё
            </button>
            <p class="text-xs text-gray-400">
                Можно выбрать один или несколько подходов.
            </p>
        </div>
    `;
}

// Собирает временное состояние фильтров только для preview-count в кнопке "Показать результаты".
// Простыми словами: пользователь еще не применил фильтр к каталогу, но мы уже можем посчитать, сколько специалистов будет найдено при текущем выборе чекбоксов.
export function buildCatalogMethodsTentativeFilters({
    catalogRuntimeState,
    normalizeCatalogFilters,
}) {
    return normalizeCatalogFilters({
        ...catalogRuntimeState.filters,
        method_ids: getCatalogMethodsModalValues(),
    });
}

// Рисует модалку фильтра "Подход" и подключает ее поведение.
// Бизнес-смысл: показать пользователю все методы сразу, дать отмечать чекбоксы и после каждого изменения пересчитывать preview-count.
export function renderCatalogMethodsModal({
    modalContent,
    catalogRuntimeState,
    schedulePreviewRefresh,
    escapeHtml,
    readJsonScript,
}) {
    const selectedMethodIds = normalizeCatalogMethodIds(catalogRuntimeState.filters.method_ids);
    modalContent.innerHTML = buildCatalogMethodsModalHtml({
        selectedMethodIds,
        escapeHtml,
        readJsonScript,
    });

    initCollapsibleList({
        containerSelector: "#catalog-methods-grid",
        buttonSelector: "#catalog-show-more-methods",
        visibleCount: 0,
    });

    const methodsGrid = document.getElementById("catalog-methods-grid");
    if (!methodsGrid) return;

    methodsGrid.addEventListener("change", (event) => {
        if (!event.target.closest(".catalog-method-checkbox")) return;
        schedulePreviewRefresh();
    });
}
