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
    formatMinLabel,
    formatMaxLabel,
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
    const minDisplay = minDisplaySelector ? getSliderElement(minDisplaySelector) : null;
    const maxDisplay = maxDisplaySelector ? getSliderElement(maxDisplaySelector) : null;
    const minBubble = getSliderElement(minBubbleSelector);
    const maxBubble = getSliderElement(maxBubbleSelector);
    const fill = getSliderElement(fillSelector);
    const minBubbleTop = "4.2rem";
    const maxBubbleTop = "0.2rem";

    if (!minInput || !maxInput || !minBubble || !maxBubble || !fill) {
        return null;
    }

    // Держит сверху тот бегунок, с которым пользователь работает прямо сейчас.
    // Это нужно, чтобы при встрече бегунков один из них не блокировал второй.
    function setActiveHandle(handleName) {
        if (handleName === "min") {
            minInput.style.zIndex = "3";
            maxInput.style.zIndex = "2";
            return;
        }

        maxInput.style.zIndex = "3";
        minInput.style.zIndex = "2";
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

    // Зажимает центр bubble-лейбла внутри доступной ширины ползунка.
    // Это нужно, чтобы подписи на крайних значениях не выходили за левую и правую границу модалки.
    function clampBubbleCenter(centerPx, bubbleWidth, rootWidth) {
        const halfWidth = bubbleWidth / 2;
        const minCenter = halfWidth;
        const maxCenter = Math.max(rootWidth - halfWidth, halfWidth);

        return Math.min(Math.max(centerPx, minCenter), maxCenter);
    }

    // Выставляет bubble-лейблы так, чтобы они не выходили за края модалки.
    // Бизнес-правило здесь простое и постоянное:
    // - значение min всегда показываем под своим бегунком;
    // - значение max всегда показываем над своим бегунком.
    // Благодаря этому при встрече бегунков подписи остаются читаемыми и не требуют дополнительного "разведения".
    function updateBubblePositions(minPercent, maxPercent) {
        const rootWidth = root.clientWidth || 0;
        const minWidth = minBubble.offsetWidth || 0;
        const maxWidth = maxBubble.offsetWidth || 0;

        if (rootWidth <= 0) {
            return;
        }

        const minCenterPx = (minPercent / 100) * rootWidth;
        const maxCenterPx = (maxPercent / 100) * rootWidth;

        const safeMinCenterPx = clampBubbleCenter(minCenterPx, minWidth, rootWidth);
        const safeMaxCenterPx = clampBubbleCenter(maxCenterPx, maxWidth, rootWidth);

        minBubble.style.left = `${safeMinCenterPx}px`;
        maxBubble.style.left = `${safeMaxCenterPx}px`;
        minBubble.style.top = minBubbleTop;
        maxBubble.style.top = maxBubbleTop;
        minBubble.style.transform = "translateX(-50%)";
        maxBubble.style.transform = "translateX(-50%)";
    }

    // Обновляет подписи и заливку активного диапазона после любого изменения ползунка.
    function renderSliderState(currentMin, currentMax) {
        if (minDisplay) {
            minDisplay.textContent = String(currentMin);
        }
        if (maxDisplay) {
            maxDisplay.textContent = String(currentMax);
        }
        minBubble.textContent = typeof formatMinLabel === "function"
            ? formatMinLabel(currentMin)
            : String(currentMin);
        maxBubble.textContent = typeof formatMaxLabel === "function"
            ? formatMaxLabel(currentMax)
            : String(currentMax);

        const minPercent = toPercent(currentMin);
        const maxPercent = toPercent(currentMax);

        fill.style.left = `${minPercent}%`;
        fill.style.width = `${Math.max(maxPercent - minPercent, 0)}%`;

        updateBubblePositions(minPercent, maxPercent);
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
        setActiveHandle("min");
        applyRangeValues(minInput.value, maxInput.value, { emitChange: true });
    }

    // Обрабатывает изменение правого бегунка "до".
    function handleMaxInput() {
        setActiveHandle("max");
        let nextMin = Number.parseInt(minInput.value, 10);
        let nextMax = Number.parseInt(maxInput.value, 10);

        if (Number.isInteger(nextMin) && Number.isInteger(nextMax) && nextMax < nextMin) {
            nextMax = nextMin;
        }

        applyRangeValues(nextMin, nextMax, { emitChange: true });
    }

    minInput.addEventListener("pointerdown", () => setActiveHandle("min"));
    maxInput.addEventListener("pointerdown", () => setActiveHandle("max"));
    minInput.addEventListener("focus", () => setActiveHandle("min"));
    maxInput.addEventListener("focus", () => setActiveHandle("max"));

    minInput.addEventListener("input", handleMinInput);
    maxInput.addEventListener("input", handleMaxInput);

    setActiveHandle("max");
    applyRangeValues(initialMin, initialMax);

    // После открытия модалки браузеру нужен один кадр, чтобы посчитать реальную ширину скрытого ранее контейнера.
    // Повторный рендер на следующем кадре ставит bubble-лейблы на правильные позиции сразу после показа модалки.
    window.requestAnimationFrame(() => {
        applyRangeValues(minInput.value, maxInput.value);
        minBubble.classList.add("is-ready");
        maxBubble.classList.add("is-ready");
    });

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
