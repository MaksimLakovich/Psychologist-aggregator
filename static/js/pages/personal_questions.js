import { initCollapsibleList } from "../modules/collapsible_list.js";
import { initToggleGroup } from "../modules/toggle_group_single_choice.js";
import { initAutosaveMethods } from "../modules/autosave_methods.js";
import { initMultiToggle } from "../modules/toggle_group_multi_choice.js"
import { initAutosaveHasPreferences } from "../modules/autosave_has_preferences.js"

document.addEventListener("DOMContentLoaded", () => {
    // получаем опции из контейнера (data-attributes) - безопасно
    const methodsContainer = document.getElementById("methods-container");
    const saveUrl = methodsContainer ? methodsContainer.dataset.saveUrl : null;
    const csrfToken = methodsContainer ? methodsContainer.dataset.csrfToken : null;

    // 1. Логика работы переключателя ИЛИ/ИЛИ (например, "Все равно" / "Есть пожелания" гдн показываем набор предпочтения для выбора или нет)
    initToggleGroup({
        anyBtn: "#btn-any",
        prefsBtn: "#btn-has-prefs",
        blockSelector: "#methods-wrapper",
        initialValue: window.HAS_PREFERENCES, // это по умолчанию устанавливает на странице то значение, которое указано в БД изначально
    });

    // 2. Автосохранение выбранного значения "has_preferences" в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    initAutosaveHasPreferences({
        saveUrl: window.API_SAVE_HAS_PREFS,
        csrfToken: window.CSRF_TOKEN,
        anyBtnSelector: "#btn-any",
        prefsBtnSelector: "#btn-has-prefs",
        debounceMs: 500,
    });

    // 3. Логика отображения списка с предпочитаемыми методами - разворачивание/сворачивание справочника
    initCollapsibleList({
        containerSelector: "#methods-grid",
        buttonSelector: "#show-more-methods",
        visibleCount: 6,
    });

    // 4. Автосохранение выбранных чекбоксом предпочитаемых методов в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    initAutosaveMethods({
        checkboxSelector: "input[name='preferred_methods']",
        saveUrl,
        csrfToken,
    });

    // 5. Логика работы МНОЖЕСТВЕННОГО выбора доступных опций (например, для выбора пола: "Мужчина" / "Женщина")
    initMultiToggle({
        containerSelector: "#ps-gender-block",
        buttonSelector: ".ps-gender-btn",
        hiddenInputsContainerSelector: "#ps-gender-hidden-inputs",
        inputName: "preferred_ps_gender",
    })

});
