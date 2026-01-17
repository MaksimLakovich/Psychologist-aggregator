import { initCollapsibleList } from "../modules/collapsible_methods_list.js";
import { initCollapsibleTopicGroups } from "../modules/collapsible_topics_list.js";
import { initToggleGroup } from "../modules/toggle_group_single_choice.js";
import { initAutosaveMethods } from "../modules/autosave_methods.js";
import { initMultiToggle } from "../modules/toggle_group_multi_choice.js";
import { initAutosaveHasPreferences } from "../modules/autosave_has_preferences.js";
import { initAutosavePreferredTopicType } from "../modules/autosave_topic_type.js";
import { initAutosaveTopics } from "../modules/autosave_topics.js";
import { initToggleTopicBlocks } from "../modules/toggle_topic_blocks.js";
import { initAutosavePreferredGender } from "../modules/autosave_gender.js";
import { initAutosavePreferredAge } from "../modules/autosave_age.js";
import { initMatchPsychologists } from "../modules/match_psychologists.js";
import { initAutosaveHasTimePreferences } from "../modules/autosave_has_time_preferences.js";

document.addEventListener("DOMContentLoaded", () => {
    // безопасно получаем опции из контейнера (data-attributes) - для METHOD
    const methodsContainer = document.getElementById("methods-container");
    const methodsSaveUrl = methodsContainer ? methodsContainer.dataset.saveUrl : null;
    const methodsCsrfToken = methodsContainer ? methodsContainer.dataset.csrfToken : null;
    // безопасно получаем опции из контейнера (data-attributes) - для TOPIC
    const topicsContainer = document.getElementById("topics-container");
    const topicsSaveUrl = topicsContainer ? topicsContainer.dataset.saveUrl : null;
    const topicsCsrfToken = topicsContainer ? topicsContainer.dataset.csrfToken : null;

    // 1. Логика работы переключателя ИЛИ/ИЛИ (кнопка: "Индивидуальная" / "Парная" где показываем нужный набор значений)
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

    // 4. Логика отображения сгруппированного списка тем с ЧЕКБОКСАМИ (6 по умолчанию + показать еще) - разворачивание/сворачивание справочника
    initCollapsibleTopicGroups();

    // 5. Автосохранение выбранных чекбоксом предпочитаемых ТЕМ в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    // инициализация topics - используем topicsSaveUrl
    initAutosaveTopics({
        checkboxSelector: "input[name='requested_topics']",
        saveUrl: topicsSaveUrl,
        csrfToken: topicsCsrfToken || window.CSRF_TOKEN,
    });

    // 6. Логика работы переключателя ИЛИ/ИЛИ (кнопка: "Все равно" / "Есть пожелания" где показываем набор предпочтения для выбора или нет)
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

    // 7. Автосохранение выбранного значения "has_preferences" в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    initAutosaveHasPreferences({
        saveUrl: window.API_SAVE_HAS_PREFS,
        csrfToken: window.CSRF_TOKEN,
        anyBtnSelector: "#btn-any",
        prefsBtnSelector: "#btn-has-prefs",
        debounceMs: 500,
    });

    // 8. Логика отображения списка методов с ЧЕКБОКСАМИ (6 по умолчанию + показать еще) - разворачивание/сворачивание справочника
    initCollapsibleList({
        containerSelector: "#methods-grid",
        buttonSelector: "#show-more-methods",
        visibleCount: 6,
    });

    // 9. Автосохранение выбранных чекбоксом предпочитаемых МЕТОДОВ в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    // инициализация methods - используем methodsSaveUrl
    initAutosaveMethods({
        checkboxSelector: "input[name='preferred_methods']",
        saveUrl: methodsSaveUrl,
        csrfToken: methodsCsrfToken || window.CSRF_TOKEN,
    });

    // 10. Логика работы МНОЖЕСТВЕННОГО выбора доступных опций для выбора ПОЛА: "Мужчина" / "Женщина"
    initMultiToggle({
        containerSelector: "#ps-gender-block",
        buttonSelector: ".ps-gender-btn",
        hiddenInputsContainerSelector: "#ps-gender-hidden-inputs",
        inputName: "preferred_ps_gender",
        initialValues: window.PREFERRED_GENDER || []
    })

    // 11. Автосохранение выбранных значений "preferred_ps_gender" в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    initAutosavePreferredGender({
        containerSelector: "#ps-gender-block",
        hiddenInputsSelector: "#ps-gender-hidden-inputs input",
        saveUrl: window.API_SAVE_PREFERRED_GENDER,
        csrfToken: window.CSRF_TOKEN,
        debounceMs: 500,
    })

    // 12. Логика работы МНОЖЕСТВЕННОГО выбора доступных опций для выбора ВОЗРАСТА: "От 25 до 35" / "От 55" / и так далее
    initMultiToggle({
        containerSelector: "#ps-age-block",
        buttonSelector: ".ps-age-btn",
        hiddenInputsContainerSelector: "#ps-age-hidden-inputs",
        inputName: "preferred_ps_age",
        initialValues: window.PREFERRED_AGE || []
    });

    // 13. Автосохранение выбранных значений "preferred_ps_age" в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    initAutosavePreferredAge({
        containerSelector: "#ps-age-block",
        hiddenInputsSelector: "#ps-age-hidden-inputs input",
        saveUrl: window.API_SAVE_PREFERRED_AGE,
        csrfToken: window.CSRF_TOKEN,
        debounceMs: 500,
    })

    // 14. Логика работы переключателя ИЛИ/ИЛИ (кнопка: "Любое" / "конкретное" где показываем набор предпочтения для выбора или нет)
    initToggleGroup({
        firstBtn: "#btn-any-time",
        secondBtn: "#btn-certain-time",
        valFirst: false, // мы используем false/true потому что в поле HAS_TIME_PREFERENCES используется boolean
        valSecond: true,
        blockToToggleSelector: "#time-slots-wrapper", // показываем выбор временных слотов, когда выбран "Конкретное"
        initialValue: window.HAS_TIME_PREFERENCES,
        hiddenInputSelector: "#input-has-time-preferences",
        showBlockWhen: "second",
    });

    // 15. Автосохранение выбранного значения "has_time_preferences" в БД без нажатия кнопки "Далее" (для моментальной фильтрации психологов)
    initAutosaveHasTimePreferences({
        saveUrl: window.API_SAVE_HAS_TIME_PREFS,
        csrfToken: window.CSRF_TOKEN,
        anyBtnSelector: "#btn-any-time",
        prefsBtnSelector: "#btn-certain-time",
        debounceMs: 500,
    });

    // Слушаем изменения на странице и, при их наличии, автоматически сразу запускаем процесс фильтрации психолога по указанным клиентом параметрам
    initMatchPsychologists();

});
