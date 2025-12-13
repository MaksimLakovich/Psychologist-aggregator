// ШАГ 1: Используем helper в autosave-файлах чтоб при срабатывании данного автосохранения срабатывал и
// client_profile_events.js, который отвечает за запуск фильтрации психологов

import { dispatchClientProfileUpdated } from "../events/client_profile_events.js";

// Шаг 2: Автосохранение выбора пола психолога.

function debounce(fn, wait = 500) {
    let t = null;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), wait);
    };
}

export function initAutosavePreferredGender({
    containerSelector,
    hiddenInputsSelector,
    saveUrl,
    csrfToken,
    debounceMs = 500,
} = {}) {

    if (!containerSelector || !hiddenInputsSelector || !saveUrl) {
        console.error("initAutosavePreferredGender: missing required parameters");
        return;
    }

    const container = document.querySelector(containerSelector);
    if (!container) {
        console.warn("initAutosavePreferredGender: container not found:", containerSelector);
        return;
    }

    // Читает значения из скрытых input - это истинное состояние
    function readValues() {
        return Array.from(document.querySelectorAll(hiddenInputsSelector))
            .map(input => input.value)
            .filter(v => v && v.trim() !== "");
    }

    // Отправляет POST запрос на API
    function doSave(values) {
        const params = new URLSearchParams();
        values.forEach(v => params.append("preferred_ps_gender", v));

        return fetch(saveUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": csrfToken,
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
                console.log("Автосохранение preferred_ps_gender:", data);
            })
            .catch((err) => {
                console.error("Ошибка автосохранения preferred_ps_gender:", err);
            });
    }

    const debouncedSave = debounce(() => {
        const values = readValues();
        doSave(values);
    }, debounceMs);

    // Навешиваем обработчик кликов по кнопкам выбора пола.
    container.addEventListener("click", (e) => {
        const btn = e.target.closest(".ps-gender-btn");
        if (!btn) return;

        // Дожидаемся syncHiddenInputs из initMultiToggle
        setTimeout(() => {
            debouncedSave();
        }, 0);
    });

    console.log("initAutosavePreferredGender: initialized");
}
