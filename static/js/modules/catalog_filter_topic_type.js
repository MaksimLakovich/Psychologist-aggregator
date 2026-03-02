import { initMultiToggle } from "./toggle_group_multi_choice.js";

/**
 * Фильтр для каталога "ВИД КОНСУЛЬТАЦИИ" (фильтр по типу тем - "Индивидуальная/Парная").
 *
 * Бизнес-задача этого файла:
 * - показать пользователю модалку выбора формата консультации;
 * - понять, выбрал ли пользователь "Индивидуальная", "Парная" или оставил поиск без ограничения;
 * - передать странице каталога готовые функции для preview-count, применения фильтра и подсветки кнопки фильтра.
 */

export const CATALOG_TOPIC_TYPE_FILTER_KEY = "consultation_type";
export const CATALOG_TOPIC_TYPE_FILTER_NAME = "Вид консультации";

// Кешируем справочник вариантов, чтобы не читать один и тот же json_script много раз за жизнь страницы.
let cachedConsultationTypeChoices = null;

// Читает с backend справочник доступных значений фильтра "Вид консультации".
// Простыми словами: именно отсюда берем, какие варианты вообще можно показать пользователю в модалке.
export function getCatalogTopicTypeChoices({ readJsonScript }) {
    if (cachedConsultationTypeChoices !== null) {
        return cachedConsultationTypeChoices;
    }

    const rawChoices = readJsonScript("catalog-consultation-type-choices-data", {});
    cachedConsultationTypeChoices = rawChoices && typeof rawChoices === "object" ? rawChoices : {};
    return cachedConsultationTypeChoices;
}

// Приводит входное значение фильтра к допустимому состоянию каталога.
// Если пришло некорректное значение, возвращаем null, чтобы каталог работал в безопасном режиме "без фильтра по виду консультации" и показывал всех специалистов.
export function normalizeCatalogTopicType(rawValue, { readJsonScript }) {
    if (typeof rawValue !== "string") return null;

    const choices = getCatalogTopicTypeChoices({ readJsonScript });
    return Object.prototype.hasOwnProperty.call(choices, rawValue) ? rawValue : null;
}

// Возвращает человекочитаемую подпись вида консультации по его техническому ключу.
// Эта логика относится именно к справочнику "Вид консультации", поэтому она живет здесь и переиспользуется, например, фильтром "Симптомы".
export function resolveCatalogTopicTypeLabel(consultationType, { readJsonScript }) {
    if (!consultationType) return null;

    const choices = getCatalogTopicTypeChoices({ readJsonScript });
    const rawLabel = choices[consultationType];
    return typeof rawLabel === "string" ? rawLabel : null;
}

// Проверяет, применен ли сейчас фильтр "Вид консультации" в каталоге.
// Если функция возвращает true, страница понимает, что кнопка фильтра в каталоге должна подсветиться как активная.
export function isCatalogTopicTypeFilterActive(filters, { readJsonScript }) {
    return Boolean(normalizeCatalogTopicType(filters?.consultation_type, { readJsonScript }));
}

// Рендерит HTML модалки фильтра "Вид консультации"
// Рисует содержимое модального окна для фильтра "Вид консультации" и подключает его поведение.
// Бизнес-смысл: дать пользователю выбрать один формат консультации или снять выбор совсем, чтобы вернуться в режим "показывать всех специалистов".
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

    // Для каталога нужен сценарий "выбрать 1 вариант или снять выбор совсем".
    // Простыми словами: пользователь может включить фильтр, поменять его или полностью убрать ограничение.
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

// Читает текущее выбранное значение прямо из открытой модалки фильтра.
// Если в модалке сейчас ничего не выбрано, возвращаем null, чтобы страница понимала: пользователь оставил каталог без ограничения по виду консультации.
// Зачем это нужно:
// 1) чтобы при нажатии Показать результаты страница поняла, какой именно фильтр надо применить;
// 2) и чтобы еще до нажатия кнопки можно было посчитать preview-count.
export function getCatalogTopicTypeModalValue({ readJsonScript }) {
    const hiddenInput = document.querySelector("#catalog-consultation-hidden-inputs input");
    return normalizeCatalogTopicType(hiddenInput ? hiddenInput.value : null, { readJsonScript });
}

// Собирает временное состояние фильтров, которое нужно только для preview-count в кнопке "Показать результаты".
// Простыми словами: пользователь еще не применил фильтр к каталогу, но мы уже можем посчитать, сколько специалистов будет найдено при текущем выборе в модалке.
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
