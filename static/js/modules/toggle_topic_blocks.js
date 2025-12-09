// Универсальный модуль для переключения видимых блоков тем при выборе вида консультации.
// Работает отдельно от логики "стиля кнопок" (initToggleGroup) и только управляет DOM-блоками,
// hidden-input и доступностью (aria-pressed). Также эмитит событие "preferredTopicType:change".

export function initToggleTopicBlocks({
    firstBtnSelector = "#btn-individual",
    secondBtnSelector = "#btn-couple",
    firstBlockSelector = "#topics-individual",
    secondBlockSelector = "#topics-couple",
    hiddenInputSelector = "#input-preferred-topic-type",
    // допустимые значения для first/second (соотносятся с value hidden input)
    valFirst = "individual",
    valSecond = "couple",
    // начальное значение (подставляется с сервера), если undefined - будет использовано valFirst
    initialValue = undefined,
} = {}) {

    const btnFirst = document.querySelector(firstBtnSelector);
    const btnSecond = document.querySelector(secondBtnSelector);
    const blockFirst = document.querySelector(firstBlockSelector);
    const blockSecond = document.querySelector(secondBlockSelector);
    const hiddenInput = hiddenInputSelector ? document.querySelector(hiddenInputSelector) : null;

    if (!btnFirst || !btnSecond) {
        console.warn("initToggleTopicBlocks: кнопки не найдены", { firstBtnSelector, secondBtnSelector });
        return;
    }
    if (!blockFirst || !blockSecond) {
        console.warn("initToggleTopicBlocks: один из блоков тем не найден", { firstBlockSelector, secondBlockSelector });
        return;
    }

    // Вспомогательная функция: показать/скрыть блоки и обновить hidden input/aria
    function apply(which) {
        if (which === "first") {
            blockFirst.classList.remove("hidden");
            blockSecond.classList.add("hidden");
            btnFirst.setAttribute("aria-pressed", "true");
            btnSecond.setAttribute("aria-pressed", "false");
            if (hiddenInput) hiddenInput.value = valFirst;
            // эмитируем событие, чтобы другие модули могли на это подписаться
            document.dispatchEvent(new CustomEvent("preferredTopicType:change", { detail: { value: valFirst } }));
        } else {
            blockSecond.classList.remove("hidden");
            blockFirst.classList.add("hidden");
            btnSecond.setAttribute("aria-pressed", "true");
            btnFirst.setAttribute("aria-pressed", "false");
            if (hiddenInput) hiddenInput.value = valSecond;
            document.dispatchEvent(new CustomEvent("preferredTopicType:change", { detail: { value: valSecond } }));
        }
    }

    // Обработчики кликов - только переключают блоки и hidden input.
    btnFirst.addEventListener("click", (e) => {
        e.preventDefault();
        apply("first");
    });

    btnSecond.addEventListener("click", (e) => {
        e.preventDefault();
        apply("second");
    });

    // Инициализация: решаем начальное состояние
    const resolvedInitial = (typeof initialValue !== "undefined") ? initialValue : valFirst;
    if (resolvedInitial == valFirst) apply("first");
    else apply("second");

    // Возвращаем API на случай unit-test / внешних управлений
    return {
        showFirst: () => apply("first"),
        showSecond: () => apply("second"),
    };
}
