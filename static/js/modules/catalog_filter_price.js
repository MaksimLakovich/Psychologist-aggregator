import { initMultiToggle } from "./toggle_group_multi_choice.js";
import { resolveCatalogTopicTypeLabel } from "./catalog_filter_topic_type.js";

/**
 * Фильтр каталога "Цена".
 *
 * Бизнес-задача этого файла:
 * - показать пользователю фиксированные значения стоимости сессии кнопками;
 * - учитывать связь фильтра "Цена" с фильтром "Вид консультации";
 * - передать странице каталога готовые функции для preview-count, применения фильтра и подсветки кнопки фильтра.
 */

export const CATALOG_PRICE_FILTER_KEY = "price_filter";
export const CATALOG_PRICE_FILTER_NAME = "Цена";

// Кешируем значения цен каталога, чтобы не читать один и тот же json_script много раз за жизнь страницы.
let cachedCatalogPriceChoices = null;

// Читает с backend доступные значения цен для фильтра "Цена".
// Простыми словами: именно отсюда берем все фиксированные цены для индивидуальной и парной консультации.
export function getCatalogPriceChoices({ readJsonScript }) {
    if (cachedCatalogPriceChoices !== null) {
        return cachedCatalogPriceChoices;
    }

    const rawChoices = readJsonScript("catalog-price-choices-data", {});
    const individualChoices = Array.isArray(rawChoices?.individual) ? rawChoices.individual : [];
    const coupleChoices = Array.isArray(rawChoices?.couple) ? rawChoices.couple : [];

    cachedCatalogPriceChoices = {
        individual: individualChoices,
        couple: coupleChoices,
    };
    return cachedCatalogPriceChoices;
}

// Собирает один общий список цен без дублей.
// Это нужно для сценария, когда "Вид консультации" не выбран и пользователь должен увидеть один общий ряд кнопок.
function getCombinedCatalogPriceChoices({ readJsonScript }) {
    const priceChoices = getCatalogPriceChoices({ readJsonScript });
    const combinedPriceValues = [
        ...priceChoices.individual,
        ...priceChoices.couple,
    ];

    return Array.from(new Set(
        combinedPriceValues
            .map((value) => Number.parseInt(String(value), 10))
            .filter((value) => Number.isInteger(value) && value > 0),
    )).sort((leftValue, rightValue) => leftValue - rightValue);
}

// Приводит выбранные цены к чистому и безопасному виду.
// Простыми словами: оставляем только те цены, которые реально доступны в каталоге, и убираем дубли.
export function normalizeCatalogPriceValues(rawValues, allowedValues) {
    if (!Array.isArray(rawValues) || !Array.isArray(allowedValues)) return [];

    const allowedValuesSet = new Set();
    allowedValues.forEach((value) => {
        const parsedValue = Number.parseInt(String(value), 10);
        if (!Number.isInteger(parsedValue) || parsedValue <= 0) return;
        allowedValuesSet.add(String(parsedValue));
    });
    const normalizedPriceValues = [];
    const seenPriceValues = new Set();

    rawValues.forEach((rawValue) => {
        const parsedValue = Number.parseInt(String(rawValue), 10);
        if (!Number.isInteger(parsedValue) || parsedValue <= 0) return;

        const normalizedValue = String(parsedValue);
        if (!allowedValuesSet.has(normalizedValue) || seenPriceValues.has(normalizedValue)) return;

        seenPriceValues.add(normalizedValue);
        normalizedPriceValues.push(normalizedValue);
    });

    return normalizedPriceValues;
}

// Приводит состояние фильтра "Цена" к единому формату каталога.
// Если уже выбран "Вид консультации", автоматически убираем цены второго формата, чтобы фильтры не противоречили друг другу.
export function normalizeCatalogPriceFilters({
    consultationType,
    priceIndividualValues,
    priceCoupleValues,
    readJsonScript,
}) {
    const priceChoices = getCatalogPriceChoices({ readJsonScript });
    const normalizedIndividualValues = normalizeCatalogPriceValues(
        priceIndividualValues,
        priceChoices.individual,
    );
    const normalizedCoupleValues = normalizeCatalogPriceValues(
        priceCoupleValues,
        priceChoices.couple,
    );

    if (consultationType === "individual") {
        return {
            price_individual_values: normalizedIndividualValues,
            price_couple_values: [],
        };
    }

    if (consultationType === "couple") {
        return {
            price_individual_values: [],
            price_couple_values: normalizedCoupleValues,
        };
    }

    return {
        price_individual_values: normalizedIndividualValues,
        price_couple_values: normalizedCoupleValues,
    };
}

// Проверяет, применен ли сейчас фильтр "Цена" в каталоге.
// Если функция возвращает true, страница понимает, что кнопка фильтра "Цена" должна подсветиться как активная.
export function isCatalogPriceFilterActive(filters, { readJsonScript }) {
    const normalizedPriceFilters = normalizeCatalogPriceFilters({
        consultationType: filters?.consultation_type ?? null,
        priceIndividualValues: filters?.price_individual_values,
        priceCoupleValues: filters?.price_couple_values,
        readJsonScript,
    });

    return normalizedPriceFilters.price_individual_values.length > 0
        || normalizedPriceFilters.price_couple_values.length > 0;
}

// Читает текущее выбранное состояние цены прямо из открытой модалки фильтра.
// Это нужно и для применения фильтра, и для предварительного подсчета количества найденных специалистов.
export function getCatalogPriceModalValues({ consultationType, readJsonScript }) {
    const commonValues = Array.from(
        document.querySelectorAll("#catalog-price-common-hidden-inputs input"),
    ).map((input) => input.value);
    const individualValues = Array.from(
        document.querySelectorAll("#catalog-price-individual-hidden-inputs input"),
    ).map((input) => input.value);
    const coupleValues = Array.from(
        document.querySelectorAll("#catalog-price-couple-hidden-inputs input"),
    ).map((input) => input.value);

    if (!consultationType) {
        return normalizeCatalogPriceFilters({
            consultationType,
            priceIndividualValues: commonValues,
            priceCoupleValues: commonValues,
            readJsonScript,
        });
    }

    return normalizeCatalogPriceFilters({
        consultationType,
        priceIndividualValues: individualValues,
        priceCoupleValues: coupleValues,
        readJsonScript,
    });
}

// Определяет, какие секции цен нужно показать пользователю в модалке.
// Если уже выбран "Вид консультации", показываем только нужный формат. Если не выбран, показываем один общий ряд цен без дублей.
function getVisiblePriceSections({ catalogRuntimeState }) {
    if (catalogRuntimeState.filters.consultation_type === "individual") {
        return ["individual"];
    }

    if (catalogRuntimeState.filters.consultation_type === "couple") {
        return ["couple"];
    }

    return ["common"];
}

// Превращает число цены в аккуратную подпись на кнопке.
// Простыми словами: добавляем пробелы между тысячами, чтобы цену было легче считывать глазами.
function formatPriceLabel(priceValue) {
    return new Intl.NumberFormat("ru-RU").format(priceValue);
}

// Собирает HTML содержимого модалки фильтра "Цена".
// Простыми словами: превращает список фиксированных цен в набор кнопок, по которым пользователь может быстро выбрать нужные значения.
export function buildCatalogPriceModalHtml({
    catalogRuntimeState,
    normalizedPriceFilters,
    escapeHtml,
    readJsonScript,
}) {
    const priceChoices = getCatalogPriceChoices({ readJsonScript });
    const visibleSections = getVisiblePriceSections({ catalogRuntimeState });

    if (!visibleSections.length) {
        return `
            <p class="text-sm text-gray-500 leading-relaxed">
                Цены пока не добавлены.
            </p>
        `;
    }

    const sectionsHtml = visibleSections.map((sectionKey) => {
        const priceValues = sectionKey === "common"
            ? getCombinedCatalogPriceChoices({ readJsonScript })
            : Array.isArray(priceChoices[sectionKey]) ? priceChoices[sectionKey] : [];
        const typeTitle = sectionKey === "common"
            ? "Все форматы"
            : resolveCatalogTopicTypeLabel(sectionKey, { readJsonScript }) || sectionKey;
        const blockId = sectionKey === "individual"
            ? "catalog-price-individual-block"
            : sectionKey === "couple"
                ? "catalog-price-couple-block"
                : "catalog-price-common-block";
        const buttonClass = sectionKey === "individual"
            ? "catalog-price-individual-btn"
            : sectionKey === "couple"
                ? "catalog-price-couple-btn"
                : "catalog-price-common-btn";
        const hiddenWrapId = sectionKey === "individual"
            ? "catalog-price-individual-hidden-inputs"
            : sectionKey === "couple"
                ? "catalog-price-couple-hidden-inputs"
                : "catalog-price-common-hidden-inputs";
        const selectedValues = sectionKey === "individual"
            ? normalizedPriceFilters.price_individual_values
            : sectionKey === "couple"
                ? normalizedPriceFilters.price_couple_values
                : normalizeCatalogPriceValues(
                    [
                        ...normalizedPriceFilters.price_individual_values,
                        ...normalizedPriceFilters.price_couple_values,
                    ],
                    getCombinedCatalogPriceChoices({ readJsonScript }),
                );

        const buttonsHtml = priceValues.map((priceValue) => `
            <button
                type="button"
                data-value="${priceValue}"
                class="${buttonClass} px-4 py-2 rounded-lg border text-base font-medium"
            >
                ${escapeHtml(formatPriceLabel(priceValue))}
            </button>
        `).join("");

        return `
            <section class="space-y-3">
                ${visibleSections.length > 1 ? `
                    <div class="pt-2 pb-1 border-b border-slate-100">
                        <p class="text-sm font-black uppercase tracking-[0.2em] text-slate-400">${escapeHtml(typeTitle)}</p>
                    </div>
                ` : ""}
                <div id="${blockId}" class="grid grid-cols-2 sm:grid-cols-3 gap-3 max-w-xl">
                    ${buttonsHtml || '<p class="text-sm text-gray-500">Цены не найдены.</p>'}
                </div>
                <div id="${hiddenWrapId}" class="hidden"></div>
            </section>
        `;
    }).join("");

    const helperText = catalogRuntimeState.filters.consultation_type
        ? "Показаны цены только для выбранного вида консультации"
        : "Показаны все доступные цены без разделения по виду консультации";

    return `
        <div class="space-y-4">
            <p class="text-sm text-gray-500 leading-relaxed">
                Выберите одну или несколько фиксированных цен, по которым хотите отфильтровать каталог
            </p>
            ${sectionsHtml}
            <p class="text-xs text-gray-400">
                ${helperText}
            </p>
        </div>
    `;
}

// Собирает временное состояние фильтров только для preview-count в кнопке "Показать результаты".
// Простыми словами: пользователь еще не применил фильтр к каталогу, но мы уже можем посчитать, сколько специалистов будет найдено при текущем выборе цен.
export function buildCatalogPriceTentativeFilters({
    catalogRuntimeState,
    normalizeCatalogFilters,
    readJsonScript,
}) {
    return normalizeCatalogFilters({
        ...catalogRuntimeState.filters,
        ...getCatalogPriceModalValues({
            consultationType: catalogRuntimeState.filters.consultation_type,
            readJsonScript,
        }),
    });
}

// Рисует модалку фильтра "Цена" и подключает ее поведение.
// Бизнес-смысл: показать пользователю доступные фиксированные цены и дать включать несколько значений внутри одного формата консультации.
export function renderCatalogPriceModal({
    modalContent,
    catalogRuntimeState,
    schedulePreviewRefresh,
    escapeHtml,
    readJsonScript,
}) {
    const normalizedPriceFilters = normalizeCatalogPriceFilters({
        consultationType: catalogRuntimeState.filters.consultation_type,
        priceIndividualValues: catalogRuntimeState.filters.price_individual_values,
        priceCoupleValues: catalogRuntimeState.filters.price_couple_values,
        readJsonScript,
    });

    modalContent.innerHTML = buildCatalogPriceModalHtml({
        catalogRuntimeState,
        normalizedPriceFilters,
        escapeHtml,
        readJsonScript,
    });

    const visibleSections = getVisiblePriceSections({ catalogRuntimeState });

    if (visibleSections.includes("individual")) {
        initMultiToggle({
            containerSelector: "#catalog-price-individual-block",
            buttonSelector: ".catalog-price-individual-btn",
            hiddenInputsContainerSelector: "#catalog-price-individual-hidden-inputs",
            inputName: "price_individual_values",
            initialValues: normalizedPriceFilters.price_individual_values,
        });
    }

    if (visibleSections.includes("couple")) {
        initMultiToggle({
            containerSelector: "#catalog-price-couple-block",
            buttonSelector: ".catalog-price-couple-btn",
            hiddenInputsContainerSelector: "#catalog-price-couple-hidden-inputs",
            inputName: "price_couple_values",
            initialValues: normalizedPriceFilters.price_couple_values,
        });
    }

    if (visibleSections.includes("common")) {
        const commonInitialValues = normalizeCatalogPriceValues(
            [
                ...normalizedPriceFilters.price_individual_values,
                ...normalizedPriceFilters.price_couple_values,
            ],
            getCombinedCatalogPriceChoices({ readJsonScript }),
        );

        initMultiToggle({
            containerSelector: "#catalog-price-common-block",
            buttonSelector: ".catalog-price-common-btn",
            hiddenInputsContainerSelector: "#catalog-price-common-hidden-inputs",
            inputName: "price_common_values",
            initialValues: commonInitialValues,
        });
    }

    visibleSections.forEach((sectionKey) => {
        const blockId = sectionKey === "individual"
            ? "catalog-price-individual-block"
            : sectionKey === "couple"
                ? "catalog-price-couple-block"
                : "catalog-price-common-block";
        const buttonClass = sectionKey === "individual"
            ? ".catalog-price-individual-btn"
            : sectionKey === "couple"
                ? ".catalog-price-couple-btn"
                : ".catalog-price-common-btn";
        const sectionBlock = document.getElementById(blockId);
        if (!sectionBlock) return;

        sectionBlock.addEventListener("click", (event) => {
            if (!event.target.closest(buttonClass)) return;

            // Даем toggle-модулю один animation frame, чтобы он успел обновить hidden-input'ы,
            // и только потом считаем preview-count.
            window.requestAnimationFrame(() => {
                schedulePreviewRefresh();
            });
        });
    });
}
