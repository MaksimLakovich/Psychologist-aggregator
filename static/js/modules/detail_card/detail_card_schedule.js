/**
 * Бизнес-смысл модуля:
 * Клиенту важно быстро понять, когда можно записаться к психологу.
 * Этот модуль превращает сырые слоты API в понятный UI:
 * "ближайшее время", группировку по дням и выбор конкретного времени.
 */

// Функция для преобразования слота в Date (берем start_iso или day+start_time)
export function getSlotDateObj(slot) {
    if (!slot) return null;

    if (slot.start_iso) {
        const dateObj = new Date(slot.start_iso);
        return Number.isNaN(dateObj.getTime()) ? null : dateObj;
    }

    if (slot.day && slot.start_time) {
        const dateObj = new Date(`${slot.day}T${slot.start_time}`);
        return Number.isNaN(dateObj.getTime()) ? null : dateObj;
    }

    return null;
}

// Функция для форматирования даты/времени/день недели в TZ клиента, чтобы клиент видел запись в своем времени
export function formatSlotParts(slot, timeZone) {
    const dateObj = getSlotDateObj(slot);
    if (!dateObj) return null;

    const datePart = new Intl.DateTimeFormat("ru-RU", {
        day: "numeric",
        month: "long",
        timeZone,
    }).format(dateObj);

    const timePart = new Intl.DateTimeFormat("ru-RU", {
        hour: "2-digit",
        minute: "2-digit",
        timeZone,
    }).format(dateObj);

    const weekdayShort = new Intl.DateTimeFormat("ru-RU", {
        weekday: "short",
        timeZone,
    }).format(dateObj).toLowerCase();

    const weekdayLong = new Intl.DateTimeFormat("ru-RU", {
        weekday: "long",
        timeZone,
    }).format(dateObj).toLowerCase();

    return { datePart, timePart, weekdayShort, weekdayLong };
}

// Функция для форматирование СЛОТА под "31 января в 05:00" в блоке "БЛИЖАЙШЕЕ ВРЕМЯ"
export function formatNearestSlot(slot, timeZone) {
    const parts = formatSlotParts(slot, timeZone);
    if (!parts) return null;
    return `${parts.datePart} в ${parts.timePart} (${parts.weekdayShort})`;
}

// Функция для группировки СЛОТОВ по ДНЯМ для вывода в блоке РАСПИСАНИЕ, для удобной навигации клиента по расписанию.
export function groupScheduleByDay(schedule = []) {
    const groups = {};

    schedule.forEach(slot => {
        const day = slot.day;
        if (!day) return;
        if (!groups[day]) groups[day] = [];
        groups[day].push(slot);
    });

    return groups;
}

// Функция для генерации ключа слота, чтобы стабильно отмечать выбранное время. (нужен для сравнения выбранного слота)
export function getSlotKey(slot) {
    return slot.start_iso || `${slot.day}T${slot.start_time}`;
}

// Функция возвращает CSS‑класс кнопки слота в зависимости от выбранности
function getSlotButtonClass(isSelected) {
    const baseClasses = [
        "rounded-full",
        "px-3",
        "py-2",
        "text-sm",
        "font-medium",
        "border",
        "transition-all",
        "duration-200",
    ];

    const selectedClasses = [
        "bg-indigo-500",
        "text-white",
        "border-indigo-500",
        "hover:bg-indigo-900",
    ];

    const idleClasses = [
        "bg-indigo-100",
        "text-gray-500",
        "border-indigo-100",
        "hover:bg-indigo-200",
    ];

    return [
        ...baseClasses,
        ...(isSelected ? selectedClasses : idleClasses),
    ].join(" ");
}

// Применяем визуальное состояние к кнопке слота (быстрое переключение визуального состояния кнопки выбранного слота)
export function applySlotButtonState(btn, isSelected) {
    btn.className = getSlotButtonClass(isSelected);
}

// Рендерим HTML блока "Расписание" (группировка по дням + кнопки слотов)
export function renderScheduleList(schedule = [], selectedSlotKey = null, daysToShow = null) {
    if (!schedule.length) {
        return `<p class="text-gray-500 text-sm mt-2">Нет доступных слотов</p>`;
    }

    const grouped = groupScheduleByDay(schedule);
    const days = Object.keys(grouped).sort();
    const visibleDays = daysToShow ? days.slice(0, daysToShow) : days;

    return visibleDays.map(day => {
        const dateObj = new Date(`${day}T00:00:00`);
        const dayLabel = Number.isNaN(dateObj.getTime())
            ? day
            : new Intl.DateTimeFormat("ru-RU", {
                day: "numeric",
                month: "long",
            }).format(dateObj);

        const weekdayLong = Number.isNaN(dateObj.getTime())
            ? ""
            : new Intl.DateTimeFormat("ru-RU", {
                weekday: "long",
            }).format(dateObj).toLowerCase();

        const times = grouped[day]
            .sort((a, b) => (a.start_time || "").localeCompare(b.start_time || ""))
            .map(slot => {
                const slotKey = getSlotKey(slot);
                const isSelected = selectedSlotKey && slotKey === selectedSlotKey;

                return `
                    <button
                        type="button"
                        class="${getSlotButtonClass(isSelected)}"
                        data-slot-key="${slotKey}"
                        data-day="${slot.day || ""}"
                        data-start-time="${slot.start_time || ""}"
                        data-start-iso="${slot.start_iso || ""}"
                    >
                        ${slot.start_time}
                    </button>
                `;
            })
            .join("");

        return `
            <div class="mt-3 py-1">
                <div class="text-lg font-semibold text-gray-700">${dayLabel}${weekdayLong ? ` (${weekdayLong})` : ""}</div>
                <div class="mt-2 flex flex-wrap gap-2">${times}</div>
            </div>
        `;
    }).join("");
}

// Обновляем строку "Ближайшая запись"
export function updateNearestSlotUI(nearestSlotText) {
    const nearestSlotEl = document.getElementById("ps-nearest-slot");
    if (!nearestSlotEl) return;
    nearestSlotEl.textContent = nearestSlotText || "Нет доступных слотов";
}

// Обновляем блок расписания (контейнер расписания)
export function updateScheduleUI(schedule, selectedSlotKey = null, daysToShow = null) {
    const scheduleEl = document.getElementById("psychologist-schedule-list");
    if (!scheduleEl) return;
    scheduleEl.innerHTML = renderScheduleList(schedule, selectedSlotKey, daysToShow);
}

// Функция для кнопки СВЕРНУТЬ / РАЗВЕРНУТЬ (расписание - ДНИ / СЛОТЫ)
export function createScheduleToggleButton() {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "mt-3 italic text-sm font-medium text-indigo-500 hover:text-indigo-900";
    btn.dataset.state = "collapsed";
    btn.textContent = "Показать больше";
    return btn;
}

export function updateScheduleToggleButton(btn, isExpanded) {
    btn.dataset.state = isExpanded ? "expanded" : "collapsed";
    btn.textContent = isExpanded ? "Показать меньше" : "Показать больше";
}
