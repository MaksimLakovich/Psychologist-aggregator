/**
 * Инициализация month-widget для страницы "Запланированные сессии".
 *
 * Бизнес-смысл:
 * - справа от списка встреч клиент видит компактный календарь текущего месяца;
 * - на каждом дне календарь показывает, есть ли в этот день встречи и сколько их;
 * - клиент может быстро листать месяцы назад/вперед и визуально понимать свою загрузку по сессиям.
 */

function readPlannedSessionsCalendarData() {
    const dataElement = document.getElementById("planned-sessions-calendar-data");
    if (!dataElement?.textContent) {
        return [];
    }

    try {
        const parsed = JSON.parse(dataElement.textContent);
        return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
        console.warn("Не удалось прочитать данные для календаря запланированных сессий:", error);
        return [];
    }
}

function buildDayCounters(events) {
    return (events || []).reduce((accumulator, eventItem) => {
        if (!eventItem?.day_key) {
            return accumulator;
        }
        const dayKey = String(eventItem.day_key);
        accumulator[dayKey] = (accumulator[dayKey] || 0) + 1;
        return accumulator;
    }, {});
}

function renderDayCounter(dayCellElement, count) {
    if (!dayCellElement || !count) {
        return;
    }

    if (dayCellElement.querySelector(".planned-session-count-badge")) {
        return;
    }

    const dayTop = dayCellElement.querySelector(".fc-daygrid-day-top");
    if (!dayTop) {
        return;
    }

    const badge = document.createElement("span");
    badge.className = "planned-session-count-badge";
    badge.textContent = String(count);
    badge.title = `${count} ${count === 1 ? "встреча" : "встречи"} в этот день`;
    dayTop.appendChild(badge);
}

function initPlannedSessionsCalendarWidget() {
    const calendarContainer = document.getElementById("planned-sessions-calendar-widget");
    if (!calendarContainer || typeof FullCalendar === "undefined") {
        return;
    }

    const events = readPlannedSessionsCalendarData();
    const dayCounters = buildDayCounters(events);
    const initialDate = calendarContainer.dataset.initialDate || undefined;

    const calendar = new FullCalendar.Calendar(calendarContainer, {
        locale: "ru",
        initialView: "dayGridMonth",
        initialDate,
        height: "auto",
        fixedWeekCount: false,
        dayMaxEvents: false,
        headerToolbar: {
            left: "prev",
            center: "title",
            right: "next",
        },
        events,
        eventDisplay: "none",
        dayCellDidMount(info) {
            const dayKey = `${info.date.getFullYear()}-${String(info.date.getMonth() + 1).padStart(2, "0")}-${String(info.date.getDate()).padStart(2, "0")}`;
            const dayCount = dayCounters[dayKey] || 0;
            renderDayCounter(info.el, dayCount);
        },
    });

    calendar.render();
}

document.addEventListener("DOMContentLoaded", initPlannedSessionsCalendarWidget);
