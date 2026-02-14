/* ============================================================================
 * Функция для проверки факта выбора МИНИМУМ одной TOPIC при попытке перейти на следующую страницу
 * ========================================================================== */

export function initCheckRequestedTopics() {
    const topicsRequiredAlert = document.getElementById("topics-required-alert");
    const stepChoiceLink = document.getElementById("step-choice-psychologist-link");
    const formEl = document.getElementById("personal-questions-form");
    const submitBtn = document.getElementById("btn-submit-filters");
    const topicsContainer = document.getElementById("topics-container");
    const preferredTopicTypeInput = document.getElementById("input-preferred-topic-type");

    // 1) Определяем, какой тип консультации (ИНДИВИДУАЛЬНАЯ/ПАРНАЯ) сейчас выбран пользователем.
    // Это значение хранится в скрытом input (его обновляет другой JS-модуль при клике на "Индивидуальная/Парная").
    function getPreferredTopicType() {
        if (preferredTopicTypeInput && preferredTopicTypeInput.value) {
            return preferredTopicTypeInput.value;
        }
        return null;
    }

    // 2) Находим активный DOM-блок с темами, который сейчас показан пользователю.
    // Логика:
    // - если known type = individual то берем блок #topics-individual
    // - если known type = couple то берем блок #topics-couple
    // - если type неизвестен (на всякий случай), то ищем блок без класса hidden
    function getActiveTopicsBlock() {
        const preferredType = getPreferredTopicType();
        if (preferredType === "individual") {
            return document.getElementById("topics-individual");
        }
        if (preferredType === "couple") {
            return document.getElementById("topics-couple");
        }
        const individualBlock = document.getElementById("topics-individual");
        if (individualBlock && !individualBlock.classList.contains("hidden")) {
            return individualBlock;
        }
        return document.getElementById("topics-couple");
    }

    // 3) Считаем количество отмеченных чекбоксов ТОЛЬКО внутри активного блока.
    // Это ключевая логика: выбранные ранее темы другого типа не должны учитываться.
    // ЭТО ВАЖНО ДЛЯ РАБОТЫ ЛОГИКИ ЗАПРЕТА ИДТИ ДАЛЬШЕ ЕСЛИ НЕ ВЫБРАНА НИ ОДНА ТЕМА (выводим плашку - выбери тему)
    function getSelectedTopicsCount() {
        const activeBlock = getActiveTopicsBlock();
        if (!activeBlock) return 0;
        return activeBlock.querySelectorAll("input[name='requested_topics']:checked").length;
    }

    // 4) Показываем плашку предупреждения
    function showTopicsRequiredAlert() {
        if (!topicsRequiredAlert) return;
        topicsRequiredAlert.classList.remove("hidden");
        scrollToAlert();
    }

    function hideTopicsRequiredAlert() {
        if (!topicsRequiredAlert) return;
        topicsRequiredAlert.classList.add("hidden");
    }

    // 5) Скролл к плашке при ее появлении, чтобы пользователь сразу увидел причину блокировки
    function scrollToAlert() {
        if (!topicsRequiredAlert) return;
        topicsRequiredAlert.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    // 6) Проверка перед переходом на следующий шаг.
    // Если в активном блоке нет выбранных тем - отменяем submit и показываем предупреждение
    function ensureTopicsSelected(e) {
        if (getSelectedTopicsCount() === 0) {
            e.preventDefault();
            showTopicsRequiredAlert();
            return false;
        }
        return true;
    }

    if (formEl) {
        formEl.addEventListener("submit", (e) => {
            ensureTopicsSelected(e);
        });
    }

    if (submitBtn) {
        submitBtn.addEventListener("click", (e) => {
            ensureTopicsSelected(e);
        });
    }

    if (stepChoiceLink) {
        stepChoiceLink.addEventListener("click", (e) => {
            ensureTopicsSelected(e);
        });
    }

    // 7) Если пользователь кликает чекбоксы, скрываем предупреждение как только появилась хотя бы одна тема
    if (topicsContainer) {
        topicsContainer.addEventListener("change", (e) => {
            const target = e.target;
            if (target && target.matches("input[name='requested_topics']")) {
                if (getSelectedTopicsCount() > 0) {
                    hideTopicsRequiredAlert();
                }
            }
        });
    }

    // 8) При переключении типа консультации убираем предупреждение,
    // чтобы оно не "залипало" из предыдущего режима.
    document.addEventListener("preferredTopicType:change", () => {
        hideTopicsRequiredAlert();
    });
}
