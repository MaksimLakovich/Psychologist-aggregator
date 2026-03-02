import { initMultiToggle } from "./toggle_group_multi_choice.js";

/**
 * Фильтр для каталога "ВИД КОНСУЛЬТАЦИИ" (фильтр по типу тем - "Индивидуальная/Парная").
 *
 * Бизнес-задача этого файла:
 * - отрисовать модалку фильтра "Вид консультации";
 * - прочитать и нормализовать выбранное значение;
 * - дать странице каталога готовые функции для preview и применения фильтра.
 */

export const CATALOG_TOPIC_TYPE_FILTER_KEY = "consultation_type";
export const CATALOG_TOPIC_TYPE_FILTER_NAME = "Вид консультации";

let cachedConsultationTypeChoices = null;


// 1) Функция читает справочник вариантов вида консультации из json_script.
// Это единый источник истины для подписей кнопок в модалке.
export function getCatalogTopicTypeChoices({ readJsonScript }) {
    if (cachedConsultationTypeChoices !== null) {
        return cachedConsultationTypeChoices;
    }

    const rawChoices = readJsonScript("catalog-consultation-type-choices-data", {});
    cachedConsultationTypeChoices = rawChoices && typeof rawChoices === "object" ? rawChoices : {};
    return cachedConsultationTypeChoices;
}

// 2) Функция нормализует входное значение фильтра "Вид консультации".
// Если значение невалидно, возвращаем null, то есть режим "показать всех".
export function normalizeCatalogTopicType(rawValue, { readJsonScript }) {
    if (typeof rawValue !== "string") return null;

    const choices = getCatalogTopicTypeChoices({ readJsonScript });
    return Object.prototype.hasOwnProperty.call(choices, rawValue) ? rawValue : null;
}

// 3) Функция возвращает русскую подпись типа консультации по его техническому ключу.
// Это нужно второму фильтру "Симптомы", чтобы понять, какие группы тем показывать в модалке.
export function resolveCatalogTopicTypeLabel(consultationType, { readJsonScript }) {
    if (!consultationType) return null;

    const choices = getCatalogTopicTypeChoices({ readJsonScript });
    const rawLabel = choices[consultationType];
    return typeof rawLabel === "string" ? rawLabel : null;
}

// 4) Функция проверяет, активен ли фильтр "Вид консультации".
// Если значение выбрано, чип фильтра на странице должен подсветиться.
export function isCatalogTopicTypeFilterActive(filters, { readJsonScript }) {
    return Boolean(normalizeCatalogTopicType(filters?.consultation_type, { readJsonScript }));
}

// 5) Функция читает текущее выбранное значение фильтра прямо из открытой модалки.
// Если активных кнопок нет, возвращаем null.
export function getCatalogTopicTypeModalValue({ readJsonScript }) {
    const hiddenInput = document.querySelector("#catalog-consultation-hidden-inputs input");
    return normalizeCatalogTopicType(hiddenInput ? hiddenInput.value : null, { readJsonScript });
}

// 6) Функция собирает временное состояние фильтров для preview-count.
// Это нужно, когда пользователь только переключает кнопки в модалке, но еще не нажал "Показать результаты".
export function buildCatalogTopicTypeTentativeFilters({
    catalogRuntimeState,
    normalizeCatalogFilters,
    readJsonScript,
}) {
    return normalizeCatalogFilters({
        ...catalogRuntimeState.filters,
        consultation_type: getCatalogTopicTypeModalValue({ readJsonScript }),
        topic_ids: catalogRuntimeState.filters.topic_ids,
    });
}

/**
 * Рендерит HTML модалки фильтра "Вид консультации".
 *
 * Бизнес-логика:
 * - показываем 2 кнопки: "Индивидуальная" и "Парная";
 * - можно выбрать одну кнопку или снять выбор совсем;
 * - после каждого изменения просим страницу пересчитать preview-count.
 */
export function renderCatalogTopicTypeModal({
    modalContent,
    catalogRuntimeState,
    schedulePreviewRefresh,
    escapeHtml,
    readJsonScript,
}) {
    const consultationTypeChoices = getCatalogTopicTypeChoices({ readJsonScript });
    const individualLabel = consultationTypeChoices.individual || "Индивидуальная";
    const coupleLabel = consultationTypeChoices.couple || "Парная";
    const activeConsultationType = normalizeCatalogTopicType(
        catalogRuntimeState.filters.consultation_type,
        { readJsonScript },
    );

    modalContent.innerHTML = `
        <div class="space-y-4">
            <p class="text-sm text-gray-500 leading-relaxed">
                Выберите формат консультации для фильтрации карточек.
            </p>
            <div id="catalog-consultation-block" class="grid grid-cols-2 gap-3 max-w-md">
                <button type="button" data-value="individual" class="catalog-consultation-btn px-4 py-2 rounded-lg border text-base font-medium">
                    ${escapeHtml(individualLabel)}
                </button>
                <button type="button" data-value="couple" class="catalog-consultation-btn px-4 py-2 rounded-lg border text-base font-medium">
                    ${escapeHtml(coupleLabel)}
                </button>
            </div>
            <div id="catalog-consultation-hidden-inputs" class="hidden"></div>
            <p class="text-xs text-gray-400">
                Можно оставить оба варианта невыбранными — это режим "все специалисты".
            </p>
        </div>
    `;

    // 1) Для каталога нужен сценарий "выбрать 1 вариант или снять выбор совсем".
    // Именно поэтому используем уже существующий multi-toggle с maxSelected=1.
    initMultiToggle({
        containerSelector: "#catalog-consultation-block",
        buttonSelector: ".catalog-consultation-btn",
        hiddenInputsContainerSelector: "#catalog-consultation-hidden-inputs",
        inputName: CATALOG_TOPIC_TYPE_FILTER_KEY,
        initialValues: activeConsultationType ? [activeConsultationType] : [],
        maxSelected: 1,
    });

    const consultationBlock = document.getElementById("catalog-consultation-block");
    if (!consultationBlock) return;

    consultationBlock.addEventListener("click", (event) => {
        if (!event.target.closest(".catalog-consultation-btn")) return;

        // Даем toggle-модулю один animation frame,
        // чтобы он успел обновить hidden-input, и только потом считаем preview-count.
        window.requestAnimationFrame(() => {
            schedulePreviewRefresh();
        });
    });
}
