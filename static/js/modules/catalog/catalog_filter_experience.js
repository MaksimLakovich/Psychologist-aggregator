import { initDualRangeSlider } from "../dual_range_slider.js";

/**
 * Фильтр каталога "Опыт".
 *
 * Бизнес-задача этого файла:
 * - показать пользователю двойной ползунок диапазона стажа;
 * - понять, какой диапазон опыта пользователь задал для поиска психолога;
 * - передать странице каталога готовые функции для preview-count, применения фильтра и подсветки кнопки фильтра.
 */

export const CATALOG_EXPERIENCE_FILTER_KEY = "experience_range";
export const CATALOG_EXPERIENCE_FILTER_NAME = "Опыт";

// Кешируем границы стажа каталога, чтобы не читать один и тот же json_script много раз за жизнь страницы.
let cachedCatalogExperienceBounds = null;

// Читает с backend реальные границы стажа каталога.
// Простыми словами: именно эти min/max используются как стартовые значения ползунка и как пределы допустимого диапазона.
export function getCatalogExperienceBounds({ readJsonScript }) {
    if (cachedCatalogExperienceBounds !== null) {
        return cachedCatalogExperienceBounds;
    }

    const rawBounds = readJsonScript("catalog-experience-bounds-data", {});
    const parsedMin = Number.parseInt(String(rawBounds?.min), 10);
    const parsedMax = Number.parseInt(String(rawBounds?.max), 10);

    const safeMin = Number.isInteger(parsedMin) ? parsedMin : 0;
    const safeMax = Number.isInteger(parsedMax) ? parsedMax : 100;

    cachedCatalogExperienceBounds = safeMin <= safeMax
        ? { min: safeMin, max: safeMax }
        : { min: safeMax, max: safeMin };

    return cachedCatalogExperienceBounds;
}

// Приводит выбранный диапазон стажа к безопасному и понятному для каталога виду.
// Если после нормализации пользователь выбрал весь доступный диапазон каталога, возвращаем experience_min=null и experience_max=null, то есть считаем фильтр неактивным.
export function normalizeCatalogExperienceRange(rawExperienceMin, rawExperienceMax, { readJsonScript }) {
    const experienceBounds = getCatalogExperienceBounds({ readJsonScript });

    function parseExperienceValue(rawValue) {
        if (rawValue === "" || rawValue === null || rawValue === undefined) {
            return null;
        }

        const parsedValue = Number.parseInt(String(rawValue), 10);
        if (!Number.isInteger(parsedValue)) {
            return null;
        }

        return Math.min(experienceBounds.max, Math.max(experienceBounds.min, parsedValue));
    }

    let experienceMin = parseExperienceValue(rawExperienceMin);
    let experienceMax = parseExperienceValue(rawExperienceMax);

    if (experienceMin !== null && experienceMax !== null && experienceMin > experienceMax) {
        [experienceMin, experienceMax] = [experienceMax, experienceMin];
    }

    if (experienceMin === experienceBounds.min) {
        experienceMin = null;
    }

    if (experienceMax === experienceBounds.max) {
        experienceMax = null;
    }

    return {
        experience_min: experienceMin,
        experience_max: experienceMax,
    };
}

// Проверяет, применен ли сейчас фильтр "Опыт" в каталоге.
// Если функция возвращает true, страница понимает, что кнопка фильтра "Опыт" должна подсветиться как активная.
export function isCatalogExperienceFilterActive(filters, { readJsonScript }) {
    const normalizedRange = normalizeCatalogExperienceRange(
        filters?.experience_min,
        filters?.experience_max,
        { readJsonScript },
    );
    return normalizedRange.experience_min !== null || normalizedRange.experience_max !== null;
}

// Читает текущее значение диапазона прямо из открытой модалки опыта.
// Это нужно и для применения фильтра, и для предварительного подсчета количества найденных специалистов.
export function getCatalogExperienceModalValues({ readJsonScript }) {
    const minInput = document.getElementById("catalog-experience-range-min");
    const maxInput = document.getElementById("catalog-experience-range-max");

    return normalizeCatalogExperienceRange(
        minInput ? minInput.value : null,
        maxInput ? maxInput.value : null,
        { readJsonScript },
    );
}

// Возвращает фактические значения, которые должны стоять на ползунке в модалке.
// Если фильтр опыта еще не применен, показываем пользователю полный диапазон каталога: от общего min до общего max.
function getCatalogExperienceSliderValues({ catalogRuntimeState, readJsonScript }) {
    const experienceBounds = getCatalogExperienceBounds({ readJsonScript });
    const normalizedRange = normalizeCatalogExperienceRange(
        catalogRuntimeState.filters.experience_min,
        catalogRuntimeState.filters.experience_max,
        { readJsonScript },
    );

    return {
        min: normalizedRange.experience_min ?? experienceBounds.min,
        max: normalizedRange.experience_max ?? experienceBounds.max,
    };
}

// Собирает HTML содержимого модалки фильтра "Опыт".
// Простыми словами: рисует пользователю двойной ползунок и значения прямо на бегунках.
export function buildCatalogExperienceModalHtml({ catalogRuntimeState, readJsonScript }) {
    const experienceBounds = getCatalogExperienceBounds({ readJsonScript });
    const sliderValues = getCatalogExperienceSliderValues({ catalogRuntimeState, readJsonScript });

    return `
        <div class="space-y-5">
            <p class="text-sm text-gray-500 leading-relaxed">
                Выберите диапазон опыта психологов, которых хотите видеть в каталоге
            </p>

            <div id="catalog-experience-slider-root" class="catalog-dual-range relative px-10 pt-12 pb-14">
                <div class="absolute left-1 right-1 top-12 h-2 rounded-full bg-slate-200"></div>
                <div id="catalog-experience-slider-fill" class="absolute top-12 h-2 rounded-full bg-indigo-500"></div>

                <div id="catalog-experience-bubble-min" style="top: 4.2rem;" class="catalog-range-bubble absolute -translate-x-1/2 rounded-xl bg-indigo-600 px-3 py-1 text-base font-bold text-white shadow-md">
                    ${sliderValues.min}
                </div>
                <div id="catalog-experience-bubble-max" style="top: 0.2rem;" class="catalog-range-bubble absolute -translate-x-1/2 rounded-xl bg-indigo-600 px-3 py-1 text-base font-bold text-white shadow-md">
                    ${sliderValues.max}
                </div>

                <input
                    id="catalog-experience-range-min"
                    type="range"
                    min="${experienceBounds.min}"
                    max="${experienceBounds.max}"
                    value="${sliderValues.min}"
                    step="1"
                    aria-label="Минимальный опыт психолога"
                >
                <input
                    id="catalog-experience-range-max"
                    type="range"
                    min="${experienceBounds.min}"
                    max="${experienceBounds.max}"
                    value="${sliderValues.max}"
                    step="1"
                    aria-label="Максимальный опыт психолога"
                >
            </div>

            <p class="text-xs text-gray-400">
                Двигайте левый и правый бегунок, чтобы задать диапазон опыта. Если оставить полный диапазон, фильтр не будет ограничивать каталог
            </p>
        </div>
    `;
}

// Собирает временное состояние фильтров только для preview-count в кнопке "Показать результаты".
// Простыми словами: пользователь еще не применил опыт к каталогу, но мы уже можем посчитать, сколько специалистов попадет в выдачу при текущем положении ползунков.
export function buildCatalogExperienceTentativeFilters({
    catalogRuntimeState,
    normalizeCatalogFilters,
    readJsonScript,
}) {
    return normalizeCatalogFilters({
        ...catalogRuntimeState.filters,
        ...getCatalogExperienceModalValues({ readJsonScript }),
    });
}

// Рисует модалку фильтра "Опыт" и подключает поведение двойного ползунка.
// После любого движения бегунков сразу пересчитываем preview-count, чтобы пользователь видел, сколько специалистов будет найдено.
export function renderCatalogExperienceModal({
    modalContent,
    catalogRuntimeState,
    schedulePreviewRefresh,
    readJsonScript,
}) {
    const experienceBounds = getCatalogExperienceBounds({ readJsonScript });
    const sliderValues = getCatalogExperienceSliderValues({ catalogRuntimeState, readJsonScript });

    modalContent.innerHTML = buildCatalogExperienceModalHtml({
        catalogRuntimeState,
        readJsonScript,
    });

    initDualRangeSlider({
        rootSelector: "#catalog-experience-slider-root",
        minInputSelector: "#catalog-experience-range-min",
        maxInputSelector: "#catalog-experience-range-max",
        minBubbleSelector: "#catalog-experience-bubble-min",
        maxBubbleSelector: "#catalog-experience-bubble-max",
        fillSelector: "#catalog-experience-slider-fill",
        minBound: experienceBounds.min,
        maxBound: experienceBounds.max,
        initialMin: sliderValues.min,
        initialMax: sliderValues.max,
        formatMinLabel(value) {
            return `От ${value}`;
        },
        formatMaxLabel(value) {
            return `До ${value}`;
        },
        onChange() {
            schedulePreviewRefresh();
        },
    });
}
