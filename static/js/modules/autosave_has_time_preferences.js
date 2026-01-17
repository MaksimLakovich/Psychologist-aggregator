// ШАГ 1: Используем helper в autosave-файлах чтоб при срабатывании данного автосохранения срабатывал и
// client_profile_events.js, который отвечает за запуск фильтрации психологов

import { dispatchClientProfileUpdated } from "../events/client_profile_events.js";

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
 * Шаг 2: Автосохранение значения переключателя "has_time_preferences".
 *
 * Ожидает конфигурацию:
 * {
 *   saveUrl: ".../users/api/save-has-time-preferences/",
 *   csrfToken: "...",
 *   anyBtnSelector: "#btn-any",
 *   prefsBtnSelector: "#btn-has-prefs",
 *   debounceMs: 300
 * }
 *
 * Модуль не отвечает за визуальное переключение блоков ("показать слоты"),
 * он только отправляет значение на сервер при изменениях.
 */
export function initAutosaveHasTimePreferences({
    saveUrl,
    csrfToken,
    anyBtnSelector,
    prefsBtnSelector,
    debounceMs = 500,
}) {
    if (!saveUrl) {
        console.error("initAutosaveHasTimePreferences: saveUrl is required");
        return;
    }

    const btnAny = document.querySelector(anyBtnSelector);
    const btnPrefs = document.querySelector(prefsBtnSelector);

    if (!btnAny || !btnPrefs) {
        console.warn("initAutosaveHasTimePreferences: кнопки переключения не найдены");
        return;
    }

    /**
     * Унифицированная функция отправки значения на сервер.
     */
    const doSave = (value) => {
        const params = new URLSearchParams();
        params.append("has_time_preferences", value ? "1" : "0");

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
            .then(response => {
                if (!response.ok) throw new Error("Save failed");
                dispatchClientProfileUpdated();
                return response.json().catch(() => ({}));
            })
            .then((data) => {
                // TODO: вместо console.log - показать маленький UI-тултип/иконку "Сохранено"
                console.log("Автосохранение has_time_preferences:", data);
            })
            .catch((error) => {
                // TODO: показать пользователю notification об ошибке (UI-ошибка "Не удалось сохранить")
                console.error("Ошибка автосохранения has_time_preferences:", error);
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

    console.log("initAutosaveHasTimePreferences: initialized");
}
