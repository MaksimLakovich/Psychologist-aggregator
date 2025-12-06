import { initCollapsibleList } from "../modules/collapsible_list.js";
import { initToggleGroup } from "../modules/toggle_group_single_choice.js";
import { initAutosaveMethods } from "../modules/autosave_methods.js";
import { initMultiToggle } from "../modules/toggle_group_multi_choice.js"

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
    });

    // 2. Логика отображения списка с предпочитаемыми методами - разворачивание/сворачивание справочника
    initCollapsibleList({
        containerSelector: "#methods-grid",
        buttonSelector: "#show-more-methods",
        visibleCount: 6,
    });

    // 3. Автосохранение выбранных чекбоксом предпочитаемых методов в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    initAutosaveMethods({
        checkboxSelector: "input[name='preferred_methods']",
        saveUrl,
        csrfToken,
    });

    // 4. Логика работы МНОЖЕСТВЕННОГО выбора доступных опций (например, для выбора пола: "Мужчина" / "Женщина")
    initMultiToggle({
        containerSelector: "#ps-gender-block",
        buttonSelector: ".ps-gender-btn",
        hiddenInputsContainerSelector: "#ps-gender-hidden-inputs",
        inputName: "preferred_ps_gender",
    })

});
