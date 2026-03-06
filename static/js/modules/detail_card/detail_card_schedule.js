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

// Помощник для определения времени суток с минималистичными SVG
function getTimeOfDay(startTime) {
    if (!startTime) return null;
    const hour = parseInt(startTime.split(':')[0], 10);

    // Бизнес-правило периодов:
    // - Утро: 06:00-11:59
    // - День: 12:00-17:59
    // - Вечер: 18:00-23:59
    // - Ночь: 00:00-05:59
    // Важно: 23:00 относится к "Вечеру" (а не к "Ночи"), чтобы порядок
    // внутри дня оставался интуитивным для клиента.

    // Возвращаем подпись группы и имя SVG-файла, чтобы UI использовал
    // централизованные иконки из static/images/psychologist_profile.
    if (hour >= 6 && hour < 12) return {
        label: "Утро",
        iconFile: "morning.svg",
    };
    if (hour >= 12 && hour < 18) return {
        label: "День",
        iconFile: "midday.svg",
    };
    if (hour >= 18 && hour <= 23) return {
        label: "Вечер",
        iconFile: "evening.svg",
    };
    return {
        label: "Ночь",
        iconFile: "night.svg",
    };
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

// Функция возвращает CSS‑класс кнопки слота в зависимости от выбранности (Чистый UI, форма "пилюли")
function getSlotButtonClass(isSelected) {
    const baseClasses = [
        "w-full",
        "min-w-0",
        "flex",
        "items-center",
        "justify-center",
        "px-3",
        "py-2",
        "text-sm",
        "rounded-xl",
        "font-medium",
        "border",
        "transition-all",
        "duration-200",
    ];

    const selectedClasses = [
        "bg-indigo-500",
        "text-white",
        "border-transparent",
        "hover:bg-indigo-500",
    ];

    const idleClasses = [
        "bg-gray-100/70",
        "text-gray-500",
        "border-transparent",
        "hover:bg-gray-200/60",
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
export function renderScheduleList(
    schedule = [],
    selectedSlotKey = null,
    daysToShow = null,
    staticUrl = "/static/"
) {
    if (!schedule.length) {
        return `
            <div class="flex flex-col items-center justify-center py-12 px-4 rounded-3xl bg-gray-50 border border-gray-100">
                <svg class="w-8 h-8 text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                </svg>
                <p class="text-gray-500 text-base font-medium">Нет доступных слотов на ближайшие дни</p>
            </div>
        `;
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

        // Сортировка и группировка слотов внутри дня
        const sortedSlots = grouped[day].sort((a, b) => (a.start_time || "").localeCompare(b.start_time || ""));

        const timeOfDayGroups = {
            "Утро": [], "День": [], "Вечер": [], "Ночь": []
        };

        sortedSlots.forEach(slot => {
            const tod = getTimeOfDay(slot.start_time);
            if (tod) timeOfDayGroups[tod.label].push(slot);
        });

        const groupsHtml = Object.entries(timeOfDayGroups)
            .filter(([_, slots]) => slots.length > 0)
            .map(([label, slots], groupIndex) => {
                const tod = getTimeOfDay(slots[0].start_time);
                const iconSrc = `${staticUrl}images/psychologist_profile/${tod.iconFile}`;
                return `
                    <div class="mt-6 first:mt-4">
                        ${
                            groupIndex > 0
                                ? '<div class="hidden sm:block border-t border-gray-200/70 my-4"></div>'
                                : ""
                        }
                        <div class="flex flex-col sm:flex-row sm:items-start gap-4 sm:gap-6">
                            <div class="sm:w-24 flex-shrink-0 flex items-center gap-2 sm:pt-2">
                                <img
                                    src="${iconSrc}"
                                    alt=""
                                    aria-hidden="true"
                                    class="w-4 h-4 object-contain"
                                />
                                <span class="text-sm font-medium text-gray-400">${label}</span>
                            </div>
                            <div class="flex-1">
                                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-x-3 gap-y-4">
                                ${slots.map(slot => {
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
                                }).join("")}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join("");

        return `
            <div class="mt-3 py-1">
                <div class="text-sm font-bold text-gray-400 uppercase tracking-widest">${dayLabel}${weekdayLong ? ` (${weekdayLong})` : ""}</div>
                <div class="space-y-2 mb-4">
                    ${groupsHtml}
                </div>
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
export function updateScheduleUI(
    schedule,
    selectedSlotKey = null,
    daysToShow = null,
    staticUrl = "/static/"
) {
    const scheduleEl = document.getElementById("psychologist-schedule-list");
    if (!scheduleEl) return;
    scheduleEl.innerHTML = renderScheduleList(schedule, selectedSlotKey, daysToShow, staticUrl);
}

// Функция для кнопки СВЕРНУТЬ / РАЗВЕРНУТЬ (расписание - ДНИ / СЛОТЫ)
export function createScheduleToggleButton() {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "w-full py-4 mt-6 rounded-2xl bg-white text-base font-medium text-gray-700 hover:bg-gray-100/70 transition-colors flex items-center justify-center gap-2";
    btn.dataset.state = "collapsed";
    btn.innerHTML = `
        <span>Показать следующие дни</span>
        <svg class="w-4 h-4 text-gray-400 transition-transform duration-300" data-icon fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
    `;
    return btn;
}

export function updateScheduleToggleButton(btn, isExpanded) {
    btn.dataset.state = isExpanded ? "expanded" : "collapsed";
    btn.querySelector("span").textContent = isExpanded ? "Скрыть расписание" : "Показать следующие дни";

    const icon = btn.querySelector("[data-icon]");
    if (icon) {
        icon.style.transform = isExpanded ? "rotate(180deg)" : "rotate(0deg)";
    }
}
