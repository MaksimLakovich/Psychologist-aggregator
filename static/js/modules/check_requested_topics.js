/* ============================================================================
 * Функция для проверки факта выбора МИНИМУМ одной TOPIC при попытке перейти на следующую страницу
 * ========================================================================== */

export function initCheckRequestedTopics() {
    const topicsRequiredAlert = document.getElementById("topics-required-alert");
    const stepChoiceLink = document.getElementById("step-choice-psychologist-link");
    const formEl = document.querySelector("form");
    const submitBtn = document.getElementById("btn-submit-filters");
    const topicsContainer = document.getElementById("topics-container");

    // 1) Получаем выбранные темы из БД
    function getSelectedTopicsCount() {
        return document.querySelectorAll("input[name='requested_topics']:checked").length;
    }

    // 2) Показываем плашку предупреждения
    function showTopicsRequiredAlert() {
        if (!topicsRequiredAlert) return;
        topicsRequiredAlert.classList.remove("hidden");
        scrollToAlert();
    }

    function hideTopicsRequiredAlert() {
        if (!topicsRequiredAlert) return;
        topicsRequiredAlert.classList.add("hidden");
    }

    // 3) Скролл вверх на плашку при ее появлении, если нажали "Далее" а не выбрано ни одной темы
    function scrollToAlert() {
        if (!topicsRequiredAlert) return;
        topicsRequiredAlert.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    // 4) ЗАПУСК
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
}
