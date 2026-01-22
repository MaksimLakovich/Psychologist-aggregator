// Используем helper в autosave-файлах чтоб при срабатывании данного автосохранения срабатывал и
// client_profile_events.js, который отвечает за запуск фильтрации психологов

import { dispatchClientProfileUpdated } from "../events/client_profile_events.js";

// Вспомогательные функции (utils).

function debounce(fn, wait = 500) {
    let t = null;
    return () => {
        clearTimeout(t);
        t = setTimeout(fn, wait);
    };
}

function setsEqual(a, b) {
    if (a.size !== b.size) return false;
    for (const v of a) {
        if (!b.has(v)) return false;
    }
    return true;
}

// ГЛАВНАЯ ТОЧКА: Автосохранение выбора предпочитаемых СЛОТОВ.

export function initAutosavePreferredSlots({
    containerSelector,
    hiddenInputsSelector,
    saveUrl,
    csrfToken,
    debounceMs = 500,
} = {}) {

    const container = document.querySelector(containerSelector);
    if (!container) return;

    let lastSavedSlots = new Set();

    // Собираем текущие состояния (выбранные слоты)
    function collectSlotsSet() {
        return new Set(
            Array.from(document.querySelectorAll(hiddenInputsSelector))
                .map(input => input.value)
                .filter(Boolean)
        );
    }

    // Отправляет POST запрос на API
    function doSaveIfChanged() {
        const currentSlots = collectSlotsSet();

        // 🚫 Ничего не изменилось - ничего не делаем
        if (setsEqual(currentSlots, lastSavedSlots)) {
            return;
        }

        // 🚫 Оба состояния пустые - ничего не делаем
        if (currentSlots.size === 0 && lastSavedSlots.size === 0) {
            return;
        }

        const params = new URLSearchParams();
        currentSlots.forEach(slot => params.append("slots[]", slot));

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
                lastSavedSlots = new Set(currentSlots);  // ⚠️ Фиксируем сохраненное состояние
                dispatchClientProfileUpdated();
            })
            .catch(err => {
                console.error("preferred_slots autosave error:", err);
            });
    }

    const debouncedSave = debounce(doSaveIfChanged, debounceMs);

    // Реагируем на изменения состояния по разным кликам
    container.addEventListener("click", (e) => {
        if (container.dataset.initializing === "true") return;

        const btn = e.target.closest("button[data-value]");
        if (!btn || btn.disabled) return;

        // ⚠️ Если никаких данных из клика мы не используем
        // autosave работает ТОЛЬКО со state
        debouncedSave();
    });

    lastSavedSlots = collectSlotsSet();

    console.log("initAutosavePreferredSlots: initialized (state-based)");
}
