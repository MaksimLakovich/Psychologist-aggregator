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
    csrfToken,
    daysAhead = 7,
}) {
    const container = document.querySelector(containerSelector);
    if (!container) {
        console.warn("TimeSlotsPicker: container not found");
        return;
    }

    if (!apiUrl) {
        console.error("TimeSlotsPicker: apiUrl is required");
        return;
    }

    // Очистка контейнера
    container.innerHTML = "";

    const daysRow = document.createElement("div");
    daysRow.id = "ts-days-row";
    daysRow.className = "flex gap-2 flex-wrap";

    const slotsContainer = document.createElement("div");
    slotsContainer.id = "ts-slots-container";
    slotsContainer.className = "mt-4";

    container.appendChild(daysRow);
    container.appendChild(slotsContainer);

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
            if (!data.slots) {
                throw new Error("Invalid response format");
            }

            renderDaysAndSlots({
                slotsByDay: data.slots,
                // ВАЖНО: Передаем текущее время пользователя (nowIso) из его профиля а не сервера, чтоб потом
                // деактивировать слоты в прошлом (делаем недоступным к выбору)
                nowIso: data.now_iso,
                daysRow,
                slotsContainer,
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
    slotsContainer,
}) {
    const days = Object.keys(slotsByDay);
    if (!days.length) return;

    let activeDay = days[0]; // текущий день активен по умолчанию

    function setActiveDay(day) {
        activeDay = day;

        // обновляем стили кнопок
        daysRow.querySelectorAll("button").forEach(btn => {
            if (btn.dataset.value === day) {
                btn.classList.add(
                    "bg-indigo-500",
                    "text-white",
                    "border-indigo-100",
                    "hover:bg-indigo-900"
                );
                btn.classList.remove(
                    "bg-white",
                    "text-gray-700",
                    "border-gray-300",
                    "hover:bg-gray-50"
                );
            } else {
                btn.classList.remove(
                    "bg-indigo-500",
                    "text-white",
                    "border-indigo-100",
                    "hover:bg-indigo-900"
                );
                btn.classList.add(
                    "bg-white",
                    "text-gray-700",
                    "border-gray-300",
                    "hover:bg-gray-50"
                );
            }
        });

        // Первичная отрисовка
        renderSlotsForDay({
            day,
            slots: slotsByDay[day],
            nowIso,                     // ← проброс
            slotsContainer,
        });
    }

    // --- КНОПКИ С ДНЯМИ ---
    days.forEach(day => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.value = day;
        btn.textContent = formatDayLabel(day);
        btn.className = "px-3 py-2 rounded-lg border text-sm font-medium";

        btn.addEventListener("click", () => {
            setActiveDay(day);
        });

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
    day,
    slots,
    nowIso,
    slotsContainer,
}) {
    slotsContainer.innerHTML = "";

    const grid = document.createElement("div");
    grid.className = "grid grid-cols-4 sm:grid-cols-6 gap-2";
    grid.id = "ts-slots-grid";

    const hiddenInputsWrap = document.createElement("div");
    hiddenInputsWrap.id = "ts-hidden-inputs";
    hiddenInputsWrap.className = "hidden";

    slots.forEach(isoString => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.value = isoString;
        btn.textContent = formatTimeLabel(isoString);
        btn.className = "px-3 py-2 rounded-lg border text-sm";

        if (isoString <= nowIso) {
            btn.disabled = true;
            btn.classList.add(
                "bg-gray-100",
                "text-gray-400",
                "cursor-not-allowed"
            );
        }

        grid.appendChild(btn);
    });

    slotsContainer.appendChild(grid);
    slotsContainer.appendChild(hiddenInputsWrap);

    // --- Для кнопок с СЛОТАМИ используем СТИЛЬ из toggle_group_multi_choice.js ---
    initMultiToggle({
        containerSelector: "#ts-slots-grid",
        buttonSelector: "button:not(:disabled)",
        hiddenInputsContainerSelector: "#ts-hidden-inputs",
        inputName: "preferred_slots",
        initialValues: [],
    });
}
