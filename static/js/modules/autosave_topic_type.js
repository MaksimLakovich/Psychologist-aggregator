/**
 * Простая утилита debounce - откладывает выполнение fn до тех пор,
 * пока пользователь не прекратит действие (например, быстро нажимать кнопки).
 */
function debounce(fn, wait = 500) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), wait);
    };
}

/**
 * Автосохранение значения переключателя "preferred_topic_type".
 *
 * Ожидает конфигурацию:
 * {
 *   saveUrl: ".../users/api/save-preferred-topic-type/",
 *   csrfToken: "...",
 *   individualBtnSelector: "#btn-individual",
 *   coupleBtnSelector: "#btn-couple",
 *   debounceMs: 500
 * }
 *
 * Модуль не отвечает за визуальное переключение блоков или еще что-то,
 * он только отправляет значение на сервер при изменениях.
 */
export function initAutosavePreferredTopicType({
    saveUrl,
    csrfToken,
    individualBtnSelector,
    coupleBtnSelector,
    debounceMs = 500,
}) {

    const btnIndividual = document.querySelector(individualBtnSelector);
    const btnCouple = document.querySelector(coupleBtnSelector);

    if (!btnIndividual || !btnCouple) {
        console.warn("initAutosavePreferredTopicType: кнопки переключения не найдены");
        return;
    }

    /**
     * Унифицированная функция отправки значения на сервер.
     */
    const doSave = (value) => {
        const params = new URLSearchParams();
        params.append("preferred_topic_type", value);

        return fetch(saveUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": csrfToken || "",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            body: params.toString(),
        })
            .then((response) => {
                response.json();
            })
            .then((data) => {
                // TODO: вместо console.log - показать маленький UI-тултип/иконку "Сохранено"
                console.log("Автосохранение preferred_topic_type:", data);
            })
            .catch((error) => {
                // TODO: показать пользователю notification об ошибке (UI-ошибка "Не удалось сохранить")
                console.error("Ошибка автосохранения preferred_topic_type:", error);
            });
    };

    // Делаем автосохранение “мягким”
    const debouncedSave = debounce(doSave, debounceMs);

    /**
     * Обработчики UI -> API
     */
    btnIndividual.addEventListener("click", () => {
        debouncedSave("individual");
    });

    btnCouple.addEventListener("click", () => {
        debouncedSave("couple");
    });

    console.log("initAutosavePreferredTopicType: initialized");
}
