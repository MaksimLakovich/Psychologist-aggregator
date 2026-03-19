/**
 * Инициализация month-widget для страницы "Запланированные сессии".
 *
 * Бизнес-смысл:
 * - справа от списка встреч клиент видит компактный календарь текущего месяца;
 * - на каждом дне календарь показывает, есть ли в этот день встречи и сколько их;
 * - клиент может быстро листать месяцы назад/вперед и визуально понимать свою загрузку по сессиям.
 */

function readPlannedSessionsCalendarData() {
    // Ищем JSON-данные, которые Django уже подготовил на сервере для month-widget.
    // Это нужно, чтобы виджет сразу понимал, в какие дни у клиента уже есть сессии,
    // без дополнительного AJAX-запроса после загрузки страницы.
    const dataElement = document.getElementById("planned-sessions-calendar-data");
    if (!dataElement?.textContent) {
        return [];
    }

    try {
        // На странице нас интересует именно массив событий по дням.
        // Если сервер по какой-то причине отдаст другой формат, то безопасно возвращаем пустой список,
        // чтобы кабинет клиента не падал из-за виджета календаря.
        const parsed = JSON.parse(dataElement.textContent);
        return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
        console.warn("Не удалось прочитать данные для календаря запланированных сессий:", error);
        return [];
    }
}

function buildDayCounters(events) {
    // Превращаем список сессий в простую карту вида:
    // { "2026-03-19": 2, "2026-03-20": 1 }
    // Это нужно, чтобы в каждой ячейке месяца быстро показать,
    // сколько встреч назначено именно на этот день.
    return (events || []).reduce((accumulator, eventItem) => {
        if (!eventItem?.day_key) {
            return accumulator;
        }

        // day_key - это канонический ключ дня, который сервер уже подготовил в формате YYYY-MM-DD.
        // По нему month-widget понимает, какой именно календарный день нужно пометить счетчиком встреч.
        const dayKey = String(eventItem.day_key);
        accumulator[dayKey] = (accumulator[dayKey] || 0) + 1;
        return accumulator;
    }, {});
}

function renderDayCounter(dayCellElement, count) {
    // Если в этот день у клиента нет встреч, то и badge не нужен:
    // ячейка должна оставаться чистой и не перегруженной лишними индикаторами.
    if (!dayCellElement || !count) {
        return;
    }

    // FullCalendar может перевызывать рендер ячейки.
    // Проверяем, не добавляли ли мы badge раньше, чтобы не дублировать его в одном и том же дне.
    if (dayCellElement.querySelector(".planned-session-count-badge")) {
        return;
    }

    // Верхняя часть ячейки уже содержит номер дня.
    // Именно туда добавляем наш badge, чтобы клиент сразу видел:
    // дата + количество встреч на эту дату.
    const dayTop = dayCellElement.querySelector(".fc-daygrid-day-top");
    if (!dayTop) {
        return;
    }

    // Badge показывает компактный счетчик встреч за день.
    // При наведении в title остается текстовая расшифровка, чтобы значение было понятно без догадок.
    const badge = document.createElement("span");
    badge.className = "planned-session-count-badge";
    badge.textContent = String(count);
    badge.title = `${count} ${count === 1 ? "встреча" : "встречи"} в этот день`;
    dayTop.appendChild(badge);
}

function initPlannedSessionsCalendarWidget() {
    // Виджет нужен только на странице "Запланированные сессии".
    // Если контейнера на странице нет или библиотека FullCalendar еще не загрузилась,
    // ничего не делаем и не мешаем остальному интерфейсу клиента.
    const calendarContainer = document.getElementById("planned-sessions-calendar-widget");
    if (!calendarContainer || typeof FullCalendar === "undefined") {
        return;
    }

    // Берем уже подготовленные на сервере данные о сессиях и превращаем их в карту счетчиков по дням.
    const events = readPlannedSessionsCalendarData();
    const dayCounters = buildDayCounters(events);

    // Сервер передает месяц, который логично показать первым.
    // Например, если у клиента новая запись в будущем месяце, календарь может сразу открыться на нем.
    const initialDate = calendarContainer.dataset.initialDate || undefined;

    const calendar = new FullCalendar.Calendar(calendarContainer, {
        locale: "ru",
        // Для клиента неделя в кабинетном календаре должна начинаться с понедельника, а не с воскресенья.
        firstDay: 1,
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
        // Сами события как полоски в month-view нам не нужны.
        // В этом кабинете задача виджета другая: показать клиенту именно количество встреч по дням,
        // а не рисовать внутри ячеек длинные event bars.
        events,
        eventDisplay: "none",
        dayCellDidMount(info) {
            // Для каждой ячейки месяца FullCalendar отдает конкретную дату.
            // Переводим ее в тот же day_key формат, который использует сервер,
            // чтобы сопоставить календарный день со счетчиком встреч.
            const dayKey = `${info.date.getFullYear()}-${String(info.date.getMonth() + 1).padStart(2, "0")}-${String(info.date.getDate()).padStart(2, "0")}`;
            const dayCount = dayCounters[dayKey] || 0;

            // Если на этот день у клиента есть встречи, добавляем badge прямо в ячейку.
            renderDayCounter(info.el, dayCount);
        },
    });

    // После полной настройки виджет можно безопасно отрисовать на странице кабинета.
    calendar.render();
}

document.addEventListener("DOMContentLoaded", initPlannedSessionsCalendarWidget);
