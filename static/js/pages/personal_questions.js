import { initCollapsibleList } from "../modules/collapsible_list.js";
import { initToggleGroup } from "../modules/toggle_group_single_choice.js";
import { initAutosaveMethods } from "../modules/autosave_methods.js";
import { initMultiToggle } from "../modules/toggle_group_multi_choice.js"
import { initAutosaveHasPreferences } from "../modules/autosave_has_preferences.js"
import { initAutosavePreferredTopicType } from "../modules/autosave_topic_type.js"
import { initAutosaveTopics } from "../modules/autosave_topics.js"
import { initToggleTopicBlocks } from "../modules/toggle_topic_blocks.js";

document.addEventListener("DOMContentLoaded", () => {
    // безопасно получаем опции из контейнера (data-attributes) - для METHOD
    const methodsContainer = document.getElementById("methods-container");
    const methodsSaveUrl = methodsContainer ? methodsContainer.dataset.saveUrl : null;
    const methodsCsrfToken = methodsContainer ? methodsContainer.dataset.csrfToken : null;
    // безопасно получаем опции из контейнера (data-attributes) - для TOPIC
    const topicsContainer = document.getElementById("topics-container");
    const topicsSaveUrl = topicsContainer ? topicsContainer.dataset.saveUrl : null;
    const topicsCsrfToken = topicsContainer ? topicsContainer.dataset.csrfToken : null;

    // 1. Логика работы переключателя ИЛИ/ИЛИ (например, "Индивидуальная" / "Парная" где показываем нужный набор значений)
    initToggleGroup({
        firstBtn: "#btn-individual",
        secondBtn: "#btn-couple",
        valFirst: "individual", // мы используем "individual"/"couple" потому что так в поле PREFERRED_TOPIC_TYPE
        valSecond: "couple",
        initialValue: window.PREFERRED_TOPIC_TYPE, // это по умолчанию устанавливает на странице то значение, которое указано в БД изначально
        hiddenInputSelector: "#input-preferred-topic-type",
    });

    // 2. Автосохранение выбранного значения "preferred_topic_type" в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    initAutosavePreferredTopicType({
        saveUrl: window.API_SAVE_PREFERRED_TOPIC_TYPE,
        csrfToken: window.CSRF_TOKEN,
        individualBtnSelector: "#btn-individual",
        coupleBtnSelector: "#btn-couple",
        debounceMs: 500,
    });

    // 3. Логика переключения блоков тем - чтобы блоки (списки тем) менялись сразу при клике на кнопку "Индивидуальная" / "Парная"
    initToggleTopicBlocks({
        firstBtnSelector: "#btn-individual",
        secondBtnSelector: "#btn-couple",
        firstBlockSelector: "#topics-individual",
        secondBlockSelector: "#topics-couple",
        hiddenInputSelector: "#input-preferred-topic-type",
        valFirst: "individual",
        valSecond: "couple",
        initialValue: window.PREFERRED_TOPIC_TYPE, // берём с сервера
    });

    // 4. Автосохранение выбранных чекбоксом предпочитаемых ТЕМ в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    // инициализация topics - используем topicsSaveUrl
    initAutosaveTopics({
        checkboxSelector: "input[name='requested_topics']",
        saveUrl: topicsSaveUrl,
        csrfToken: topicsCsrfToken || window.CSRF_TOKEN,
    });

    // 5. Логика работы переключателя ИЛИ/ИЛИ (например, "Все равно" / "Есть пожелания" где показываем набор предпочтения для выбора или нет)
    initToggleGroup({
        firstBtn: "#btn-any",
        secondBtn: "#btn-has-prefs",
        valFirst: false, // мы используем false/true потому что в поле HAS_PREFERENCES используется boolean
        valSecond: true,
        blockToToggleSelector: "#methods-wrapper", // показываем методы когда второй (secondBtn) активен
        initialValue: window.HAS_PREFERENCES,
        hiddenInputSelector: "#input-has-preferences",
        showBlockWhen: "second",
    });

    // 6. Автосохранение выбранного значения "has_preferences" в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    initAutosaveHasPreferences({
        saveUrl: window.API_SAVE_HAS_PREFS,
        csrfToken: window.CSRF_TOKEN,
        anyBtnSelector: "#btn-any",
        prefsBtnSelector: "#btn-has-prefs",
        debounceMs: 500,
    });

    // 7. Логика отображения списка с ЧЕКБОКСАМИ (6 по умолчанию + показать еще) - разворачивание/сворачивание справочника
    initCollapsibleList({
        containerSelector: "#methods-grid",
        buttonSelector: "#show-more-methods",
        visibleCount: 6,
    });

    // 8. Автосохранение выбранных чекбоксом предпочитаемых МЕТОДОВ в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    // инициализация methods - используем methodsSaveUrl
    initAutosaveMethods({
        checkboxSelector: "input[name='preferred_methods']",
        saveUrl: methodsSaveUrl,
        csrfToken: methodsCsrfToken || window.CSRF_TOKEN,
    });

    // 9. Логика работы МНОЖЕСТВЕННОГО выбора доступных опций (например, для выбора пола: "Мужчина" / "Женщина")
    initMultiToggle({
        containerSelector: "#ps-gender-block",
        buttonSelector: ".ps-gender-btn",
        hiddenInputsContainerSelector: "#ps-gender-hidden-inputs",
        inputName: "preferred_ps_gender",
    })

});
