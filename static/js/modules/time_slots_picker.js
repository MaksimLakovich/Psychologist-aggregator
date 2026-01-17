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

import { initToggleGroup } from "./toggle_group_single_choice.js";
import { initMultiToggle } from "./toggle_group_multi_choice.js";

/**
 * Форматирует стиль для кнопок с выбором ДНЕЙ: например, "Пт, 16 янв", "Сб, 17 янв" и так далее...
 */
function formatDayLabel(dateStr, locale = "ru-RU") {
    const date = new Date(dateStr);
    return date.toLocaleDateString(locale, {
        weekday: "short",
        day: "numeric",
        month: "short",
    });
}

/**
 * Форматирует datetime слота в заданный стиль: "HH:MM", например, "09:00", "14:00" и так далее...
 */
function formatTimeLabel(isoString, locale = "ru-RU") {
    const date = new Date(isoString);
    return date.toLocaleTimeString(locale, {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
    });
}

/**
 * Проверка: слот в прошлом или нет и если в прошлом то деактивируем его (делаем недоступным к выбору)
 */
function isPastSlot(isoString, now = new Date()) {
    return new Date(isoString) <= now;
}

/**
 * Главная точка входа
 */
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
function renderDaysAndSlots({
    slotsByDay,
    daysRow,
    slotsContainer,
}) {
    const days = Object.keys(slotsByDay);
    if (!days.length) return;

    // --- КНОПКИ С ДНЯМИ ---
    days.forEach((day, index) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.id = `ts-day-${day}`;
        btn.dataset.value = day;
        btn.textContent = formatDayLabel(day);
        btn.className = "px-3 py-2 rounded-lg border text-sm font-medium";

        daysRow.appendChild(btn);
    });

    // --- Для кнопок с ДНЯМИ используем СТИЛЬ из toggle_group_single_choice.js ---
    initToggleGroup({
        firstBtn: `#ts-day-${days[0]}`,
        secondBtn: null, // используем кастомный режим ниже
        initialValue: days[0],
        hiddenInputSelector: null,
        customButtonsSelector: "#ts-days-row button",
        onChange: (selectedDay) => {
            renderSlotsForDay({
                day: selectedDay,
                slots: slotsByDay[selectedDay],
                slotsContainer,
            });
        },
    });

    // Первичная отрисовка
    renderSlotsForDay({
        day: days[0],
        slots: slotsByDay[days[0]],
        slotsContainer,
    });
}

/**
 * Рендер слотов конкретного дня
 */
function renderSlotsForDay({
    day,
    slots,
    slotsContainer,
}) {
    slotsContainer.innerHTML = "";

    const grid = document.createElement("div");
    grid.className = "grid grid-cols-4 sm:grid-cols-6 gap-2";
    grid.id = "ts-slots-grid";

    const hiddenInputsWrap = document.createElement("div");
    hiddenInputsWrap.id = "ts-hidden-inputs";
    hiddenInputsWrap.className = "hidden";

    const now = new Date();

    slots.forEach(isoString => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.value = isoString;
        btn.textContent = formatTimeLabel(isoString);
        btn.className = "px-3 py-2 rounded-lg border text-sm";

        if (isPastSlot(isoString, now)) {
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
