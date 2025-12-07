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
 * Автосохранение значения переключателя "has_preferences".
 *
 * Ожидает конфигурацию:
 * {
 *   saveUrl: ".../users/api/save-has-preferences/",
 *   csrfToken: "...",
 *   anyBtnSelector: "#btn-any",
 *   prefsBtnSelector: "#btn-has-prefs",
 *   debounceMs: 300
 * }
 *
 * Модуль не отвечает за визуальное переключение блоков ("показать методы"),
 * он только отправляет значение на сервер при изменениях.
 */
export function initAutosaveHasPreferences({
    saveUrl,
    csrfToken,
    anyBtnSelector,
    prefsBtnSelector,
    debounceMs = 500,
}) {
    if (!saveUrl) {
        console.error("initAutosaveHasPreferences: saveUrl is required");
        return;
    }

    const btnAny = document.querySelector(anyBtnSelector);
    const btnPrefs = document.querySelector(prefsBtnSelector);

    if (!btnAny || !btnPrefs) {
        console.warn("initAutosaveHasPreferences: кнопки переключения не найдены");
        return;
    }

    /**
     * Унифицированная функция отправки значения на сервер.
     */
    const doSave = (value) => {
        const params = new URLSearchParams();
        params.append("has_preferences", value ? "1" : "0");

        fetch(saveUrl, {
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
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                // TODO: вместо console.log - показать маленький UI-тултип/иконку "Сохранено"
                console.log("Автосохранение has_preferences:", data);
            })
            .catch((error) => {
                // TODO: показать пользователю notification об ошибке (UI-ошибка "Не удалось сохранить")
                console.error("Ошибка автосохранения has_preferences:", error);
            });
    };

    // Делаем автосохранение “мягким”
    const debouncedSave = debounce(doSave, debounceMs);

    /**
     * Обработчики UI -> API
     */
    btnAny.addEventListener("click", () => {
        debouncedSave(false);
    });

    btnPrefs.addEventListener("click", () => {
        debouncedSave(true);
    });

    console.log("initAutosaveHasPreferences: initialized");
}
