/**
 * Инициализация month-widget для страницы "Мой календарь".
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
    // Превращаем список сессий в карту по дням:
    // { "2026-03-19": 2, "2026-03-20": 1 }, где отдельно считаем:
    // - активные встречи;
    // - уже завершенные встречи.
    // Это нужно, чтобы календарный виджет мог показывать клиенту два разных типа счетчиков в одной ячейке дня.
    return (events || []).reduce((accumulator, eventItem) => {
        if (!eventItem?.day_key) {
            return accumulator;
        }

        // day_key - это канонический ключ дня, который сервер уже подготовил в формате YYYY-MM-DD.
        // По нему month-widget понимает, какой именно календарный день нужно пометить счетчиком встреч.
        const dayKey = String(eventItem.day_key);
        if (!accumulator[dayKey]) {
            accumulator[dayKey] = {
                activeCount: 0,
                completedCount: 0,
            };
        }

        if (eventItem.bucket === "completed") {
            accumulator[dayKey].completedCount += 1;
        } else {
            accumulator[dayKey].activeCount += 1;
        }

        return accumulator;
    }, {});
}

function renderDayCounter(dayCellElement, counters) {
    // counters - это уже не одно число, а объект вида:
    // {
    //   activeCount: 2,
    //   completedCount: 1
    // }
    // Он нужен, чтобы в одном и том же дне можно было показать
    // и будущие/текущие встречи, и уже прошедшие.
    const activeCount = counters?.activeCount || 0;
    const completedCount = counters?.completedCount || 0;

    // Если в этот день у клиента нет ни активных, ни завершенных встреч, то и badge не нужен:
    // ячейка должна оставаться чистой и не перегруженной лишними индикаторами.
    if (!dayCellElement || (!activeCount && !completedCount)) {
        return;
    }

    // FullCalendar может перевызывать рендер ячейки.
    // Проверяем, не добавляли ли мы badge-стек раньше, чтобы не дублировать его в одном и том же дне.
    if (dayCellElement.querySelector(".planned-session-badge-stack")) {
        return;
    }

    // Верхняя часть ячейки уже содержит номер дня.
    // Именно туда добавляем наш badge, чтобы клиент сразу видел:
    // дата + количество встреч на эту дату.
    const dayTop = dayCellElement.querySelector(".fc-daygrid-day-top");
    if (!dayTop) {
        return;
    }

    const badgeStack = document.createElement("div");
    badgeStack.className = "planned-session-badge-stack";

    // Серый badge отвечает за уже прошедшие встречи:
    // он помогает отличить историю от будущих сессий прямо внутри календаря.
    // Если на одной дате есть и архив, и активные встречи, серый badge должен быть слева.
    if (completedCount) {
        const completedBadge = document.createElement("span");
        completedBadge.className = "planned-session-count-badge planned-session-count-badge-completed";
        completedBadge.textContent = String(completedCount);
        badgeStack.appendChild(completedBadge);
    }

    // Индиго-badge отвечает за активные встречи: клиент сразу понимает,
    // что в этот день у него есть еще не завершенные сессии.
    // В паре с серым badge он должен стоять справа.
    if (activeCount) {
        const activeBadge = document.createElement("span");
        activeBadge.className = "planned-session-count-badge";
        activeBadge.textContent = String(activeCount);
        badgeStack.appendChild(activeBadge);
    }

    dayTop.appendChild(badgeStack);
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
    // Базовая query-строка нужна, чтобы при клике по дню не потерять текущий layout страницы.
    // Например:
    //   - если кабинет открыт в sidebar-layout,
    //   - клик по дню должен привести на тот же URL, но с layout=sidebar и selected_day=...
    const dayClickQueryBase = calendarContainer.dataset.dayClickQueryBase || "";
    // selectedDay приходит с сервера, если страница уже открыта в режиме фильтра по конкретной дате.
    // Это нужно только для визуальной подсветки выбранной ячейки в календаре.
    const selectedDay = calendarContainer.dataset.selectedDay || "";

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
        dateClick(info) {
            // FullCalendar отдает дату объекта Date.
            // Приводим ее к нашему каноническому формату YYYY-MM-DD,
            // который понимает серверный фильтр selected_day.
            // Если на день нет ни активных, ни завершенных встреч, клик не должен ничего делать:
            // виджет фильтрует список только по тем датам, где реально есть события.
            const dayKey = `${info.date.getFullYear()}-${String(info.date.getMonth() + 1).padStart(2, "0")}-${String(info.date.getDate()).padStart(2, "0")}`;
            const dayCount = dayCounters[dayKey] || { activeCount: 0, completedCount: 0 };
            if (!dayCount.activeCount && !dayCount.completedCount) {
                return;
            }

            // Переходим на эту же страницу, но уже с selected_day.
            // Сервер после этого сам перестроит список слева и шапку страницы.
            const queryPrefix = dayClickQueryBase || "";
            const separator = queryPrefix.includes("?") ? "&" : "?";
            window.location.assign(`${window.location.pathname}${queryPrefix}${separator}selected_day=${dayKey}`);
        },
        dayCellDidMount(info) {
            // Для каждой ячейки месяца FullCalendar отдает конкретную дату.
            // Переводим ее в тот же day_key формат, который использует сервер,
            // чтобы сопоставить календарный день со счетчиком встреч.
            const dayKey = `${info.date.getFullYear()}-${String(info.date.getMonth() + 1).padStart(2, "0")}-${String(info.date.getDate()).padStart(2, "0")}`;
            const dayCount = dayCounters[dayKey] || { activeCount: 0, completedCount: 0 };

            // Если на этот день у клиента есть встречи, добавляем badge прямо в ячейку.
            renderDayCounter(info.el, dayCount);

            // Дни с badge делаем интерактивными: клик по ним фильтрует список слева только на выбранную дату.
            if (dayCount.activeCount || dayCount.completedCount) {
                info.el.classList.add("has-session-badge");
            }

            // Если клиент уже фильтрует страницу по конкретной дате,
            // визуально подсвечиваем выбранный день в month-widget, чтобы не терялась связь между списком и календарем.
            if (selectedDay && selectedDay === dayKey) {
                info.el.classList.add("fc-day-selected");
            }
        },
    });

    // После полной настройки виджет можно безопасно отрисовать на странице кабинета.
    calendar.render();
}

document.addEventListener("DOMContentLoaded", initPlannedSessionsCalendarWidget);
