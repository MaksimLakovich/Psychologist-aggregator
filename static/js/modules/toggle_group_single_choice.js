export function initToggleGroup({ anyBtn, prefsBtn, blockSelector }) {
    const btnAny = document.querySelector(anyBtn);
    const btnPrefs = document.querySelector(prefsBtn);
    const methodsBlock = document.querySelector(blockSelector);

    if (!btnAny || !btnPrefs || !methodsBlock) return;

    function setActive(activeBtn, inactiveBtn) {
        // Активная кнопка
        activeBtn.classList.add(
            "bg-indigo-500", "text-white", "border-indigo-900"
        );
        activeBtn.classList.remove(
            "bg-white", "text-gray-700", "border-gray-300", "hover:bg-blue-50"
        );

        // Неактивная кнопка
        inactiveBtn.classList.remove(
            "bg-indigo-500", "text-white", "border-indigo-900"
        );
        inactiveBtn.classList.add(
            "bg-white", "text-gray-700", "border-gray-300", "hover:bg-blue-50"
        );
    }

    function activateAny() {
        setActive(btnAny, btnPrefs);
        methodsBlock.classList.add("hidden");
    }

    function activatePrefs() {
        setActive(btnPrefs, btnAny);
        methodsBlock.classList.remove("hidden");
    }

    btnAny.addEventListener("click", activateAny);
    btnPrefs.addEventListener("click", activatePrefs);

    // стартовое состояние по умолчанию
    activateAny();
}
