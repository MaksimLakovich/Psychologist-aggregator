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

function toTimestamp(value) {
    const ts = Date.parse(value);
    return Number.isNaN(ts) ? null : ts;
}

// ГЛАВНАЯ ТОЧКА ВХОДА
export function initTimeSlotsPicker({
    containerSelector,
    apiUrl,
    initialSelectedSlots = [],
}) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    // ❌ ЛОГИ ДЛЯ ОТЛАДКИ - потом удалить
    console.group("🧪 TimeSlotsPicker init");
    console.log("initialSelectedSlots (raw):", initialSelectedSlots);
    console.groupEnd();

    // КАНОНИЧЕСКОЕ ХРАНЕНИЕ - timestamps
    const selectedTsSet = new Set(
        initialSelectedSlots
            .map(toTimestamp)
            .filter(ts => ts !== null)
    );

    const daysRow = container.querySelector("#ts-days-row");
    const slotsGrid = container.querySelector("#ts-slots-grid");
    const hiddenInputsWrap = container.querySelector("#ts-hidden-inputs");

    const dayBtnClass = daysRow.dataset.btnClass;
    const slotBtnClass = slotsGrid.dataset.btnClass;

    fetch(apiUrl, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
    })
        .then(r => r.json())
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
                selectedTsSet,
                container,
            });
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
    selectedTsSet,
    container,
}) {
    const days = Object.keys(slotsByDay);
    if (!days.length) return;

    function setActiveDay(day) {

        // обновляем стили кнопок
        daysRow.querySelectorAll("button").forEach(btn => {
            const active = btn.dataset.value === day;

            btn.classList.toggle("bg-indigo-500", active);
            btn.classList.toggle("text-white", active);
            btn.classList.toggle("border-indigo-500", active);
            btn.classList.toggle("hover:bg-indigo-900", active);

            btn.classList.toggle("bg-indigo-100", !active);
            btn.classList.toggle("text-gray-700", !active);
            btn.classList.toggle("border-indigo-300", !active);
            btn.classList.toggle("hover:bg-indigo-200", !active);
        });

        // Рендер слотов для выбранного дня
        renderSlotsForDay({
            slots: slotsByDay[day],
            nowIso,                     // ← проброс
            slotsGrid,
            hiddenInputsWrap,
            slotBtnClass,
            selectedTsSet,
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

    // Первичная активация - текущий день активен по умолчанию
    setActiveDay(days[0]);
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
    selectedTsSet,
    container,
}) {
    slotsGrid.innerHTML = "";
    hiddenInputsWrap.innerHTML = "";

    const initialValuesForDay = [];

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

        const ts = toTimestamp(isoString);
        if (ts !== null && selectedTsSet.has(ts)) {
            initialValuesForDay.push(isoString);
        }

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
        initialValues: initialValuesForDay,
    });

    // Удаляем флаг после рендера через requestAnimationFrame
    requestAnimationFrame(() => {
        delete container.dataset.initializing;
    });
}
