/**
 * КЛИЕНТСКИЙ ВЫБОР ИНТЕРЕСУЮЩИХ СЛОТОВ
 *
 * Отвечает ТОЛЬКО за:
 * - загрузку доменных слотов (GET /get-domain-slots/)
 * - визуализацию:
 *    - дней (single toggle)
 *    - слотов дня (multi toggle)
 * - отображение ранее выбранных preferred_slots
 * - toggle (add / remove) на уровне UI
 * - disable слотов в прошлом
 *
 * НЕ отвечает за:
 * - autosave preferred_slots
 * - availability психологов
 */

import { initMultiToggle } from "./toggle_group_multi_choice.js";

// Нормализация слота из БД к ISO-формату API
// Пример:
//   "2026-01-20 10:00:00+03" → "2026-01-20T10:00:00+03:00"
function normalizeSlot(value) {
    if (!value) return null;

    // если уже ISO - то ничего не делаем
    if (value.includes("T")) return value;

    return value
        .replace(" ", "T")
        .replace(/(\+\d{2})$/, "$1:00");
}

// Задаем формат для кнопок с выбором ДНЕЙ: например, "Пт, 16 янв", "Сб, 17 янв" и так далее...
// Возвращаем объект с двумя частями: weekday и date
function formatDayLabel(dateStr) {
    // dateStr = "2026-01-17"
    const [year, month, day] = dateStr.split("-").map(Number);
    const date = new Date(year, month - 1, day);

    const weekday = date.toLocaleDateString("ru-RU", { weekday: "short" }).toUpperCase(); // ВС
    const dayMonth = date.toLocaleDateString("ru-RU", { day: "numeric", month: "short" }); // 18 янв

    return { weekday, dayMonth };
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
    csrfToken, // (оставлен для симметрии API, здесь не используется)
    initialSelectedSlots = [],
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

    // --- Получаем ранее сохраненные слоты (из БД) ---
    // нормализуем preferred_slots из БД к ISO формату API
    const selectedSet = new Set(
        (initialSelectedSlots || [])
            .map(normalizeSlot)
            .filter(Boolean)
    );

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
                selectedSet,
                container,
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
    selectedSet,
    container,
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
            btn.classList.toggle("border-indigo-500", isActive);
            btn.classList.toggle("hover:bg-indigo-900", isActive);

            btn.classList.toggle("bg-indigo-100", !isActive);
            btn.classList.toggle("text-gray-700", !isActive);
            btn.classList.toggle("border-indigo-300", !isActive);
            btn.classList.toggle("hover:bg-indigo-200", !isActive);
        });

        // Рендер слотов для выбранного дня
        renderSlotsForDay({
            slots: slotsByDay[day],
            nowIso,                     // ← проброс
            slotsGrid,
            hiddenInputsWrap,
            slotBtnClass,
            selectedSet,
            container,
        });
    }

    daysRow.innerHTML = "";

    // --- КНОПКИ С ДНЯМИ ---
    days.forEach(day => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.value = day;
        btn.className = dayBtnClass;

        const { weekday, dayMonth } = formatDayLabel(day);

        // Добавляем 2 строки в кнопку
        btn.innerHTML = `
            <div class="text-base font-bold">${weekday}</div>
            <div class="text-xs">${dayMonth}</div>
        `;

        btn.addEventListener("click", () => setActiveDay(day));
        daysRow.appendChild(btn);
    });

    // Первичная активация
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
    selectedSet,
    container,
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
                "line-through",
                "cursor-not-allowed"
            );
        }

        // При клике обновляем selectedSet
        btn.addEventListener("click", () => {
            if (btn.disabled) return;

            if (selectedSet.has(isoString)) {
                selectedSet.delete(isoString);
            } else {
                selectedSet.add(isoString);
            }
        });

        slotsGrid.appendChild(btn);
    });

    // флаг для autosave / сторонних слушателей
    container.dataset.initializing = "true";

    // --- Для кнопок с СЛОТАМИ используем СТИЛЬ из toggle_group_multi_choice.js ---
    initMultiToggle({
        containerSelector: "#ts-slots-grid",
        buttonSelector: "button:not(:disabled)",
        hiddenInputsContainerSelector: "#ts-hidden-inputs",
        inputName: "preferred_slots",
        initialValues: Array.from(selectedSet),
    });

    // Удаляем флаг после рендера через requestAnimationFrame
    requestAnimationFrame(() => {
        delete container.dataset.initializing;
    });
}
