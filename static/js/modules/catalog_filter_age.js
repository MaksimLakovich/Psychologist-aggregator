import { initDualRangeSlider } from "./dual_range_slider.js";

/**
 * Фильтр каталога "Возраст".
 *
 * Бизнес-задача этого файла:
 * - показать пользователю двойной ползунок диапазона возраста;
 * - понять, какой диапазон возраста пользователь задал для поиска психолога;
 * - передать странице каталога готовые функции для preview-count, применения фильтра и подсветки кнопки фильтра.
 */

export const CATALOG_AGE_FILTER_KEY = "age_range";
export const CATALOG_AGE_FILTER_NAME = "Возраст";

// Кешируем возрастные границы каталога, чтобы не читать один и тот же json_script много раз за жизнь страницы.
let cachedCatalogAgeBounds = null;

// Читает с backend реальные возрастные границы каталога.
// Простыми словами: именно эти min/max используются как стартовые значения ползунка и как пределы допустимого диапазона.
export function getCatalogAgeBounds({ readJsonScript }) {
    if (cachedCatalogAgeBounds !== null) {
        return cachedCatalogAgeBounds;
    }

    const rawBounds = readJsonScript("catalog-age-bounds-data", {});
    const parsedMin = Number.parseInt(String(rawBounds?.min), 10);
    const parsedMax = Number.parseInt(String(rawBounds?.max), 10);

    const safeMin = Number.isInteger(parsedMin) ? parsedMin : 18;
    const safeMax = Number.isInteger(parsedMax) ? parsedMax : 120;

    cachedCatalogAgeBounds = safeMin <= safeMax
        ? { min: safeMin, max: safeMax }
        : { min: safeMax, max: safeMin };

    return cachedCatalogAgeBounds;
}

// Приводит выбранный возрастной диапазон к безопасному и понятному для каталога виду.
// Если после нормализации пользователь выбрал весь доступный диапазон каталога, возвращаем age_min=null и age_max=null, то есть считаем фильтр неактивным.
export function normalizeCatalogAgeRange(rawAgeMin, rawAgeMax, { readJsonScript }) {
    const ageBounds = getCatalogAgeBounds({ readJsonScript });

    function parseAgeValue(rawValue) {
        if (rawValue === "" || rawValue === null || rawValue === undefined) {
            return null;
        }

        const parsedValue = Number.parseInt(String(rawValue), 10);
        if (!Number.isInteger(parsedValue)) {
            return null;
        }

        return Math.min(ageBounds.max, Math.max(ageBounds.min, parsedValue));
    }

    let ageMin = parseAgeValue(rawAgeMin);
    let ageMax = parseAgeValue(rawAgeMax);

    if (ageMin !== null && ageMax !== null && ageMin > ageMax) {
        [ageMin, ageMax] = [ageMax, ageMin];
    }

    if (ageMin === ageBounds.min) {
        ageMin = null;
    }

    if (ageMax === ageBounds.max) {
        ageMax = null;
    }

    return {
        age_min: ageMin,
        age_max: ageMax,
    };
}

// Проверяет, применен ли сейчас фильтр "Возраст" в каталоге.
// Если функция возвращает true, страница понимает, что кнопка фильтра "Возраст" должна подсветиться как активная.
export function isCatalogAgeFilterActive(filters, { readJsonScript }) {
    const normalizedRange = normalizeCatalogAgeRange(filters?.age_min, filters?.age_max, { readJsonScript });
    return normalizedRange.age_min !== null || normalizedRange.age_max !== null;
}

// Читает текущее значение диапазона прямо из открытой модалки возраста.
// Это нужно и для применения фильтра, и для предварительного подсчета количества найденных специалистов.
export function getCatalogAgeModalValues({ readJsonScript }) {
    const minInput = document.getElementById("catalog-age-range-min");
    const maxInput = document.getElementById("catalog-age-range-max");

    return normalizeCatalogAgeRange(
        minInput ? minInput.value : null,
        maxInput ? maxInput.value : null,
        { readJsonScript },
    );
}

// Возвращает фактические значения, которые должны стоять на ползунке в модалке.
// Если фильтр возраста еще не применен, показываем пользователю полный диапазон каталога: от общего min до общего max.
function getCatalogAgeSliderValues({ catalogRuntimeState, readJsonScript }) {
    const ageBounds = getCatalogAgeBounds({ readJsonScript });
    const normalizedRange = normalizeCatalogAgeRange(
        catalogRuntimeState.filters.age_min,
        catalogRuntimeState.filters.age_max,
        { readJsonScript },
    );

    return {
        min: normalizedRange.age_min ?? ageBounds.min,
        max: normalizedRange.age_max ?? ageBounds.max,
    };
}

// Собирает HTML содержимого модалки фильтра "Возраст".
// Простыми словами: рисует пользователю текущий диапазон, подписи над бегунками и сам двойной ползунок.
export function buildCatalogAgeModalHtml({ catalogRuntimeState, readJsonScript }) {
    const ageBounds = getCatalogAgeBounds({ readJsonScript });
    const sliderValues = getCatalogAgeSliderValues({ catalogRuntimeState, readJsonScript });

    return `
        <div class="space-y-5">
            <p class="text-sm text-gray-500 leading-relaxed">
                Выберите возрастной диапазон психологов, которых хотите видеть в каталоге.
            </p>

            <div class="grid grid-cols-2 gap-3">
                <div class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <p class="text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">От</p>
                    <p id="catalog-age-current-min" class="mt-1 text-2xl font-black text-indigo-700">${sliderValues.min}</p>
                </div>
                <div class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-right">
                    <p class="text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">До</p>
                    <p id="catalog-age-current-max" class="mt-1 text-2xl font-black text-indigo-700">${sliderValues.max}</p>
                </div>
            </div>

            <div id="catalog-age-slider-root" class="catalog-dual-range relative px-1 pt-12 pb-3">
                <div class="absolute left-1 right-1 top-12 h-2 rounded-full bg-slate-200"></div>
                <div id="catalog-age-slider-fill" class="absolute top-12 h-2 rounded-full bg-indigo-500"></div>

                <div id="catalog-age-bubble-min" class="absolute top-0 -translate-x-1/2 rounded-xl bg-indigo-600 px-3 py-1 text-xs font-bold text-white shadow-md">
                    ${sliderValues.min}
                </div>
                <div id="catalog-age-bubble-max" class="absolute top-0 -translate-x-1/2 rounded-xl bg-indigo-600 px-3 py-1 text-xs font-bold text-white shadow-md">
                    ${sliderValues.max}
                </div>

                <input
                    id="catalog-age-range-min"
                    type="range"
                    min="${ageBounds.min}"
                    max="${ageBounds.max}"
                    value="${sliderValues.min}"
                    step="1"
                    aria-label="Минимальный возраст психолога"
                >
                <input
                    id="catalog-age-range-max"
                    type="range"
                    min="${ageBounds.min}"
                    max="${ageBounds.max}"
                    value="${sliderValues.max}"
                    step="1"
                    aria-label="Максимальный возраст психолога"
                >
            </div>

            <p class="text-xs text-gray-400">
                Двигайте левый и правый бегунок, чтобы задать диапазон возраста. Если оставить полный диапазон, фильтр не будет ограничивать каталог.
            </p>
        </div>
    `;
}

// Собирает временное состояние фильтров только для preview-count в кнопке "Показать результаты".
// Простыми словами: пользователь еще не применил возраст к каталогу, но мы уже можем посчитать, сколько специалистов попадет в выдачу при текущем положении ползунков.
export function buildCatalogAgeTentativeFilters({
    catalogRuntimeState,
    normalizeCatalogFilters,
    readJsonScript,
}) {
    return normalizeCatalogFilters({
        ...catalogRuntimeState.filters,
        ...getCatalogAgeModalValues({ readJsonScript }),
    });
}

// Рисует модалку фильтра "Возраст" и подключает поведение двойного ползунка.
// После любого движения бегунков сразу пересчитываем preview-count, чтобы пользователь видел, сколько специалистов будет найдено.
export function renderCatalogAgeModal({
    modalContent,
    catalogRuntimeState,
    schedulePreviewRefresh,
    readJsonScript,
}) {
    const ageBounds = getCatalogAgeBounds({ readJsonScript });
    const sliderValues = getCatalogAgeSliderValues({ catalogRuntimeState, readJsonScript });

    modalContent.innerHTML = buildCatalogAgeModalHtml({
        catalogRuntimeState,
        readJsonScript,
    });

    initDualRangeSlider({
        rootSelector: "#catalog-age-slider-root",
        minInputSelector: "#catalog-age-range-min",
        maxInputSelector: "#catalog-age-range-max",
        minDisplaySelector: "#catalog-age-current-min",
        maxDisplaySelector: "#catalog-age-current-max",
        minBubbleSelector: "#catalog-age-bubble-min",
        maxBubbleSelector: "#catalog-age-bubble-max",
        fillSelector: "#catalog-age-slider-fill",
        minBound: ageBounds.min,
        maxBound: ageBounds.max,
        initialMin: sliderValues.min,
        initialMax: sliderValues.max,
        onChange() {
            schedulePreviewRefresh();
        },
    });
}
