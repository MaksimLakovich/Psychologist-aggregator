/**
 * Общий модуль двойного ползунка диапазона.
 *
 * Бизнес-задача этого файла:
 * - дать фильтрам каталога готовую механику выбора диапазона "от и до";
 * - синхронизировать оба ползунка, подписи значений и заливку активного диапазона;
 * - переиспользоваться в фильтрах, где нужен один и тот же сценарий: возраст, цена, опыт.
 */

// Инициализирует двойной ползунок диапазона и подключает его поведение.
// Простыми словами: следит, чтобы левый ползунок не уехал правее правого, а правый не уехал левее левого.
export function initDualRangeSlider({
    rootSelector,
    minInputSelector,
    maxInputSelector,
    minDisplaySelector,
    maxDisplaySelector,
    minBubbleSelector,
    maxBubbleSelector,
    fillSelector,
    minBound,
    maxBound,
    initialMin,
    initialMax,
    onChange,
}) {
    const root = document.querySelector(rootSelector);
    if (!root) return null;

    // Ищет элемент сначала внутри корневого контейнера ползунка, а если там его нет, то во всем документе.
    // Это нужно, потому что подписи "От/До" могут лежать рядом с ползунком, а не строго внутри его корневого блока.
    function getSliderElement(selector) {
        return root.querySelector(selector) || document.querySelector(selector);
    }

    const minInput = getSliderElement(minInputSelector);
    const maxInput = getSliderElement(maxInputSelector);
    const minDisplay = getSliderElement(minDisplaySelector);
    const maxDisplay = getSliderElement(maxDisplaySelector);
    const minBubble = getSliderElement(minBubbleSelector);
    const maxBubble = getSliderElement(maxBubbleSelector);
    const fill = getSliderElement(fillSelector);

    if (!minInput || !maxInput || !minDisplay || !maxDisplay || !minBubble || !maxBubble || !fill) {
        return null;
    }

    // Приводит пару значений к безопасному диапазону ползунка.
    function normalizeRangeValues(rawMin, rawMax) {
        let safeMin = Number.parseInt(String(rawMin), 10);
        let safeMax = Number.parseInt(String(rawMax), 10);

        if (!Number.isInteger(safeMin)) safeMin = minBound;
        if (!Number.isInteger(safeMax)) safeMax = maxBound;

        safeMin = Math.max(minBound, Math.min(safeMin, maxBound));
        safeMax = Math.max(minBound, Math.min(safeMax, maxBound));

        if (safeMin > safeMax) {
            safeMin = safeMax;
        }

        return {
            min: safeMin,
            max: safeMax,
        };
    }

    // Переводит значение в процент относительно полного диапазона.
    // Это нужно, чтобы правильно выставить заливку и подписи над бегунками.
    function toPercent(value) {
        if (maxBound === minBound) {
            return 0;
        }

        return ((value - minBound) / (maxBound - minBound)) * 100;
    }

    // Обновляет подписи и заливку активного диапазона после любого изменения ползунка.
    function renderSliderState(currentMin, currentMax) {
        minDisplay.textContent = String(currentMin);
        maxDisplay.textContent = String(currentMax);
        minBubble.textContent = String(currentMin);
        maxBubble.textContent = String(currentMax);

        const minPercent = toPercent(currentMin);
        const maxPercent = toPercent(currentMax);

        fill.style.left = `${minPercent}%`;
        fill.style.width = `${Math.max(maxPercent - minPercent, 0)}%`;

        minBubble.style.left = `${minPercent}%`;
        maxBubble.style.left = `${maxPercent}%`;
    }

    // Устанавливает новое состояние ползунка и при необходимости сообщает о нем наружу.
    function applyRangeValues(nextMin, nextMax, { emitChange = false } = {}) {
        const normalizedRange = normalizeRangeValues(nextMin, nextMax);

        minInput.value = String(normalizedRange.min);
        maxInput.value = String(normalizedRange.max);
        renderSliderState(normalizedRange.min, normalizedRange.max);

        if (emitChange && typeof onChange === "function") {
            onChange({
                min: normalizedRange.min,
                max: normalizedRange.max,
            });
        }
    }

    // Обрабатывает изменение левого бегунка "от".
    function handleMinInput() {
        applyRangeValues(minInput.value, maxInput.value, { emitChange: true });
    }

    // Обрабатывает изменение правого бегунка "до".
    function handleMaxInput() {
        let nextMin = Number.parseInt(minInput.value, 10);
        let nextMax = Number.parseInt(maxInput.value, 10);

        if (Number.isInteger(nextMin) && Number.isInteger(nextMax) && nextMax < nextMin) {
            nextMax = nextMin;
        }

        applyRangeValues(nextMin, nextMax, { emitChange: true });
    }

    minInput.addEventListener("input", handleMinInput);
    maxInput.addEventListener("input", handleMaxInput);

    applyRangeValues(initialMin, initialMax);

    // Возвращаем наружу простой API, чтобы фильтр мог при необходимости прочитать текущее состояние.
    return {
        getValues() {
            return normalizeRangeValues(minInput.value, maxInput.value);
        },
        setValues(nextMin, nextMax) {
            applyRangeValues(nextMin, nextMax);
        },
    };
}
