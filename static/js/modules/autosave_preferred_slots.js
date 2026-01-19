// ШАГ 1: Используем helper в autosave-файлах чтоб при срабатывании данного автосохранения срабатывал и
// client_profile_events.js, который отвечает за запуск фильтрации психологов

import { dispatchClientProfileUpdated } from "../events/client_profile_events.js";

// Шаг 2: Автосохранение выбора предпочитаемых СЛОТОВ.

function debounce(fn, wait = 500) {
    let t = null;
    return () => {
        clearTimeout(t);
        t = setTimeout(fn, wait);
    };
}

export function initAutosavePreferredSlots({
    containerSelector,
    hiddenInputsSelector,
    saveUrl,
    csrfToken,
    debounceMs = 500,
} = {}) {

    const container = document.querySelector(containerSelector);
    if (!container) return;

    function collectSlots() {
        return Array.from(
            document.querySelectorAll(hiddenInputsSelector)
        ).map(input => input.value);
    }

    // Отправляет POST запрос на API
    function doSave() {
        const slots = collectSlots();

        const params = new URLSearchParams();
        slots.forEach(slot => params.append("slots[]", slot));

        fetch(saveUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            body: params.toString(),
        })
            .then(res => {
                if (!res.ok) throw new Error("Save failed");
                dispatchClientProfileUpdated();
            })
            .catch(err => {
                console.error("preferred_slots autosave error:", err);
            });
    }

    const debouncedSave = debounce(doSave, debounceMs);

    // Реагируем на изменения состояния (через initMultiToggle)
//    container.addEventListener("click", (e) => {
//        const btn = e.target.closest("button[data-value]");
//        if (!btn || btn.disabled) return;
//
//        // Даём toggle_group_multi_choice закончить работу
//        requestAnimationFrame(() => {
//            debouncedSave();
//        });
//    });

    container.addEventListener("click", (e) => {
        if (container.dataset.initializing === "true") return;

        const btn = e.target.closest("button[data-value]");
        if (!btn || btn.disabled) return;

        const slot = btn.dataset.value;
        debouncedSave(slot);
    });

    console.log("initAutosavePreferredSlots: initialized");
}
