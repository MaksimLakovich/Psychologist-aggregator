import { initMultiToggle } from "../toggle_group_multi_choice.js";

/**
 * Фильтр каталога "Пол".
 *
 * Бизнес-задача этого файла:
 * - показать пользователю модалку выбора пола психолога;
 * - понять, выбрал ли пользователь "Мужчина", "Женщина" или оставил поиск без ограничения;
 * - передать странице каталога готовые функции для preview-count, применения фильтра и подсветки кнопки фильтра.
 */

export const CATALOG_GENDER_FILTER_KEY = "gender";
export const CATALOG_GENDER_FILTER_NAME = "Пол";

// Кешируем справочник вариантов пола, чтобы не читать один и тот же json_script много раз за жизнь страницы.
let cachedCatalogGenderChoices = null;

// Читает с backend справочник доступных значений фильтра "Пол".
// Простыми словами: именно отсюда берем, какие кнопки вообще можно показать пользователю в модалке.
export function getCatalogGenderChoices({ readJsonScript }) {
    if (cachedCatalogGenderChoices !== null) {
        return cachedCatalogGenderChoices;
    }

    const rawChoices = readJsonScript("catalog-gender-choices-data", {});
    cachedCatalogGenderChoices = rawChoices && typeof rawChoices === "object" ? rawChoices : {};
    return cachedCatalogGenderChoices;
}

// Приводит входное значение фильтра к допустимому состоянию каталога.
// Если пришло некорректное значение, возвращаем null, чтобы каталог работал в режиме "без фильтра по полу".
export function normalizeCatalogGender(rawValue, { readJsonScript }) {
    if (typeof rawValue !== "string") return null;

    const choices = getCatalogGenderChoices({ readJsonScript });
    return Object.prototype.hasOwnProperty.call(choices, rawValue) ? rawValue : null;
}

// Проверяет, применен ли сейчас фильтр "Пол" в каталоге.
// Если функция возвращает true, страница понимает, что кнопка фильтра "Пол" должна подсветиться как активная.
export function isCatalogGenderFilterActive(filters, { readJsonScript }) {
    return Boolean(normalizeCatalogGender(filters?.gender, { readJsonScript }));
}

// Читает текущее выбранное значение прямо из открытой модалки фильтра.
// Если в модалке ничего не выбрано, возвращаем null, чтобы каталог продолжал показывать и мужчин, и женщин.
export function getCatalogGenderModalValue({ readJsonScript }) {
    const hiddenInput = document.querySelector("#catalog-gender-hidden-inputs input");
    return normalizeCatalogGender(hiddenInput ? hiddenInput.value : null, { readJsonScript });
}

// Собирает временное состояние фильтров, которое нужно только для preview-count в кнопке "Показать результаты".
// Простыми словами: пользователь еще не применил фильтр к каталогу, но мы уже можем посчитать, сколько специалистов будет найдено при текущем выборе.
export function buildCatalogGenderTentativeFilters({
    catalogRuntimeState,
    normalizeCatalogFilters,
    readJsonScript,
}) {
    return normalizeCatalogFilters({
        ...catalogRuntimeState.filters,
        gender: getCatalogGenderModalValue({ readJsonScript }),
    });
}

// Рисует содержимое модального окна для фильтра "Пол" и подключает его поведение.
// Бизнес-смысл: дать пользователю выбрать один вариант пола или снять выбор совсем, чтобы вернуться в режим "все специалисты".
export function renderCatalogGenderModal({
    modalContent,
    catalogRuntimeState,
    schedulePreviewRefresh,
    escapeHtml,
    readJsonScript,
}) {
    const genderChoices = getCatalogGenderChoices({ readJsonScript });
    const maleLabel = genderChoices.male || "Мужчина";
    const femaleLabel = genderChoices.female || "Женщина";
    const activeGender = normalizeCatalogGender(catalogRuntimeState.filters.gender, { readJsonScript });

    modalContent.innerHTML = `
        <div class="space-y-4">
            <p class="text-sm pb-4 text-gray-500 leading-relaxed">
                Выберите пол психолога для фильтрации карточек
            </p>
            <div id="catalog-gender-block" class="grid grid-cols-2 pb-4 gap-3 max-w-md">
                <button type="button" data-value="male" class="catalog-gender-btn px-4 py-2 rounded-lg border text-base font-medium">
                    ${escapeHtml(maleLabel)}
                </button>
                <button type="button" data-value="female" class="catalog-gender-btn px-4 py-2 rounded-lg border text-base font-medium">
                    ${escapeHtml(femaleLabel)}
                </button>
            </div>
            <div id="catalog-gender-hidden-inputs" class="hidden"></div>
            <p class="text-xs text-gray-400">
                Можно оставить оба варианта невыбранными — это режим "все специалисты"
            </p>
        </div>
    `;

    // Для каталога нужен сценарий "выбрать 1 вариант или снять выбор совсем".
    initMultiToggle({
        containerSelector: "#catalog-gender-block",
        buttonSelector: ".catalog-gender-btn",
        hiddenInputsContainerSelector: "#catalog-gender-hidden-inputs",
        inputName: CATALOG_GENDER_FILTER_KEY,
        initialValues: activeGender ? [activeGender] : [],
        maxSelected: 1,
    });

    const genderBlock = document.getElementById("catalog-gender-block");
    if (!genderBlock) return;

    genderBlock.addEventListener("click", (event) => {
        if (!event.target.closest(".catalog-gender-btn")) return;

        // Даем toggle-модулю один animation frame, чтобы он успел обновить hidden-input,
        // и только потом считаем preview-count.
        window.requestAnimationFrame(() => {
            schedulePreviewRefresh();
        });
    });
}
