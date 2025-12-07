export function initToggleGroup({ anyBtn, prefsBtn, blockSelector, initialValue = false }) {
    const btnAny = document.querySelector(anyBtn);
    const btnPrefs = document.querySelector(prefsBtn);
    const methodsBlock = document.querySelector(blockSelector);
    const hiddenInput = document.querySelector("#input-has-preferences"); // ДОБАВЛЕНО чтоб при нажатии "Далее" не сбрасывалось значение на false в has_preferences

    if (!btnAny || !btnPrefs || !methodsBlock) return;

    function setActive(activeBtn, inactiveBtn) {
        // Активная кнопка
        activeBtn.classList.add(
            "bg-indigo-500", "text-white", "border-indigo-900", "hover:bg-indigo-900"
        );
        activeBtn.classList.remove(
            "bg-white", "text-gray-700", "border-gray-300", "hover:bg-gray-50"
        );
        // Неактивная кнопка
        inactiveBtn.classList.remove(
            "bg-indigo-500", "text-white", "border-indigo-900", "hover:bg-indigo-900"
        );
        inactiveBtn.classList.add(
            "bg-white", "text-gray-700", "border-gray-300", "hover:bg-gray-50"
        );
    }

    function activateAny() {
        setActive(btnAny, btnPrefs);
        methodsBlock.classList.add("hidden");

        if (hiddenInput) hiddenInput.value = "false";  // ДОБАВЛЕНО чтоб при нажатии "Далее" не сбрасывалось значение на false в has_preferences
    }

    function activatePrefs() {
        setActive(btnPrefs, btnAny);
        methodsBlock.classList.remove("hidden");

        if (hiddenInput) hiddenInput.value = "true";  // ДОБАВЛЕНО чтоб при нажатии "Далее" не сбрасывалось значение на false в has_preferences
    }

    btnAny.addEventListener("click", activateAny);
    btnPrefs.addEventListener("click", activatePrefs);

    // Устанавливаем состояние при загрузке страницы (данные из БД в поле has_preferences)
    if (initialValue) {
        activatePrefs();
    } else {
        activateAny();
    }

}
