/**
 * КЛИЕНТСКИЙ ВЫВБОР ИНТЕРЕСУЮЩИХ СЛОТОВ
 *
 * Отвечает ТОЛЬКО за:
 * - загрузку доменных слотов (GET /get-domain-slots/)
 * - визуализацию:
 *    - дней (single toggle)
 *    - слотов дня (multi toggle)
 * - disable слотов в прошлом
 *
 * НЕ отвечает за:
 * - autosave preferred_slots (будет следующим шагом)
 * - availability психологов
 */

import { initMultiToggle } from "./toggle_group_multi_choice.js";

// Задаем формат для кнопок с выбором ДНЕЙ: например, "Пт, 16 янв", "Сб, 17 янв" и так далее...
function formatDayLabel(dateStr) {
    // dateStr = "2026-01-17"
    const [year, month, day] = dateStr.split("-").map(Number);
    const date = new Date(year, month - 1, day);

    return date.toLocaleDateString("ru-RU", {
        weekday: "short",
        day: "numeric",
        month: "short",
    });
}

// Задаем формат для кнопок с выбором СЛОТОВ: форматируем datetime в "HH:MM", например, "09:00", "14:00" и так далее...
function formatTimeLabel(isoString) {
    // isoString у нас get_domain_slots_use_case.py возвращает в формате: "2026-01-17T00:00:00+10:00"
    return isoString.slice(11, 16); // применяем слайс и получаем эту часть: "00:00"
}

// ГЛАВНАЯ ТОЧКА ВХОДА
export function initTimeSlotsPicker({
    containerSelector,
    apiUrl,
}) {
    const container = document.querySelector(containerSelector);
    if (!container) {
        console.warn("TimeSlotsPicker: container not found");
        return;
    }

    const daysRow = container.querySelector("#ts-days-row");
    const slotsGrid = container.querySelector("#ts-slots-grid");
    const hiddenInputsWrap = container.querySelector("#ts-hidden-inputs");

    if (!daysRow || !slotsGrid || !hiddenInputsWrap) {
        console.error("TimeSlotsPicker: required DOM nodes not found");
        return;
    }

    const dayBtnClass = daysRow.dataset.btnClass;
    const slotBtnClass = slotsGrid.dataset.btnClass;

    fetch(apiUrl, {
        method: "GET",
        credentials: "same-origin",
        headers: {
            "X-Requested-With": "XMLHttpRequest",
        },
    })
        .then(res => {
            if (!res.ok) throw new Error("Failed to load domain slots");
            return res.json();
        })
        .then(data => {
            renderDaysAndSlots({
                slotsByDay: data.slots,
                // ВАЖНО: Передаем текущее время пользователя (nowIso) из его профиля а не сервера, чтоб потом
                // деактивировать слоты в прошлом (делаем недоступным к выбору)
                nowIso: data.now_iso,
                daysRow,
                slotsGrid,
                hiddenInputsWrap,
                dayBtnClass,
                slotBtnClass,
            });
        })
        .catch(err => {
            console.error("TimeSlotsPicker error:", err);
        });
}

/**
 * Рендер дней + логика переключения
 */

// nowIso: Передаем текущее время пользователя из его профиля а не сервера, чтоб потом деактивировать слоты
// в прошлом (делаем недоступным к выбору)
function renderDaysAndSlots({
    slotsByDay,
    nowIso,
    daysRow,
    slotsGrid,
    hiddenInputsWrap,
    dayBtnClass,
    slotBtnClass,
}) {
    const days = Object.keys(slotsByDay);
    if (!days.length) return;

    let activeDay = days[0]; // текущий день активен по умолчанию

    function setActiveDay(day) {
        activeDay = day;

        // обновляем стили кнопок
        daysRow.querySelectorAll("button").forEach(btn => {
            const isActive = btn.dataset.value === day;

            btn.classList.toggle("bg-indigo-500", isActive);
            btn.classList.toggle("text-white", isActive);
            btn.classList.toggle("border-indigo-100", isActive);
            btn.classList.toggle("hover:bg-indigo-900", isActive);

            btn.classList.toggle("bg-white", !isActive);
            btn.classList.toggle("text-gray-700", !isActive);
            btn.classList.toggle("border-gray-300", !isActive);
            btn.classList.toggle("hover:bg-gray-50", !isActive);
        });

        // Первичная отрисовка
        renderSlotsForDay({
            slots: slotsByDay[day],
            nowIso,                     // ← проброс
            slotsGrid,
            hiddenInputsWrap,
            slotBtnClass,
        });
    }

    daysRow.innerHTML = "";

    // --- КНОПКИ С ДНЯМИ ---
    days.forEach(day => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.value = day;
        btn.textContent = formatDayLabel(day);
        btn.className = dayBtnClass;

        btn.addEventListener("click", () => setActiveDay(day));
        daysRow.appendChild(btn);
    });

    // --- первичная активация ---
    setActiveDay(activeDay);
}

/**
 * Рендер слотов конкретного дня
 */

// nowIso: Передаем текущее время пользователя из его профиля а не сервера, чтоб потом деактивировать слоты
// в прошлом (делаем недоступным к выбору)
function renderSlotsForDay({
    slots,
    nowIso,
    slotsGrid,
    hiddenInputsWrap,
    slotBtnClass,
}) {
    slotsGrid.innerHTML = "";
    hiddenInputsWrap.innerHTML = "";

    slots.forEach(isoString => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.value = isoString;
        btn.textContent = formatTimeLabel(isoString);
        btn.className = slotBtnClass;

        if (isoString <= nowIso) {
            btn.disabled = true;
            btn.classList.add(
                "bg-gray-100",
                "text-gray-400",
                "cursor-not-allowed"
            );
        }

        slotsGrid.appendChild(btn);
    });

    // --- Для кнопок с СЛОТАМИ используем СТИЛЬ из toggle_group_multi_choice.js ---
    initMultiToggle({
        containerSelector: "#ts-slots-grid",
        buttonSelector: "button:not(:disabled)",
        hiddenInputsContainerSelector: "#ts-hidden-inputs",
        inputName: "preferred_slots",
        initialValues: [],
    });
}
