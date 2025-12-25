// Универсальный двухкнопочный переключатель (single choice)

// Конфигурация:
// {
//   firstBtn: "#selectorA",         // обязательно
//   secondBtn: "#selectorB",        // обязательно
//   valFirst: <any>,                // значение, которое означает "первая" кнопка (строка/boolean/число)
//   valSecond: <any>,               // значение для второй
//   blockToToggleSelector: null,    // optional: селектор блока, который показываем при выборе second (или first, см. map)
//   showBlockWhen: "second"|"first",// optional: при выборе какой кнопки показываем blockToToggle (по умолчанию "second")
//   initialValue: <any>,            // optional: значение по умолчанию (подставляем из server-side)
//   hiddenInputSelector = null,     // optional: чтоб когда пользователь нажимает "Далее" то Django получает значения только из hidden-input, и это нужно для обновления hidden-input при авотсохранении JS
//   activeClasses: [...],           // optional: классы, добавляемые активной кнопке
//   inactiveClasses: [...],         // optional: классы для неактивной кнопки
// }

export function initToggleGroup({
    firstBtn,
    secondBtn,
    valFirst = true,
    valSecond = false,
    blockToToggleSelector = null,
    showBlockWhen = "second",
    initialValue = undefined,
    hiddenInputSelector = null,
    activeClasses = ["bg-indigo-500", "text-white", "border-indigo-100", "hover:bg-indigo-900"],
    inactiveClasses = ["bg-white", "text-gray-700", "border-gray-300", "hover:bg-gray-50"],
} = {}) {

    const btnA = document.querySelector(firstBtn);
    const btnB = document.querySelector(secondBtn);
    const block = blockToToggleSelector ? document.querySelector(blockToToggleSelector) : null;
    const hiddenInput = hiddenInputSelector ? document.querySelector(hiddenInputSelector) : null;

    if (!btnA || !btnB) return;

    function applyActive(activeEl, inactiveEl) {
        // active
        activeClasses.forEach(c => activeEl.classList.add(c));
        inactiveClasses.forEach(c => activeEl.classList.remove(c));
        // inactive
        activeClasses.forEach(c => inactiveEl.classList.remove(c));
        inactiveClasses.forEach(c => inactiveEl.classList.add(c));
    }

    function showOrHideBlock(which) {
        if (!block) return;
        if (showBlockWhen === "second") {
            if (which === "second") block.classList.remove("hidden");
            else block.classList.add("hidden");
        } else {
            if (which === "first") block.classList.remove("hidden");
            else block.classList.add("hidden");
        }
    }

    function setFirstActive() {
        applyActive(btnA, btnB);
        showOrHideBlock("first");
        if (hiddenInput) hiddenInput.value = valFirst;
    }
    function setSecondActive() {
        applyActive(btnB, btnA);
        showOrHideBlock("second");
        if (hiddenInput) hiddenInput.value = valSecond;
    }

    btnA.addEventListener("click", () => {
        setFirstActive();
    });
    btnB.addEventListener("click", () => {
        setSecondActive();
    });

    // корректно определяем начальное значение
    const resolvedInitial = (typeof initialValue !== "undefined") ? initialValue : undefined;

    if (typeof resolvedInitial !== "undefined") {
        // сравниваем нестрого, чтобы поддержать строковые/булевы значения
        if (resolvedInitial == valFirst) {
            setFirstActive();
        } else if (resolvedInitial == valSecond) {
            setSecondActive();
        } else {
            setFirstActive();
        }
    } else {
        setFirstActive();
    }
}
