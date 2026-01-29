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
 * - показывает счетчик выбранных слотов на днях
 *
 * НЕ отвечает за:
 * - autosave preferred_slots
 * - availability психологов
 */

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

    // ДЛЯ СЧЕТЧИКА ВЫБРАННЫХ СЛОТОВ: Глобальное хранилище данных после загрузки (чтобы считать бейджи)
    let cachedSlotsByDay = {};

    function syncHiddenInputs() {
        hiddenInputsWrap.innerHTML = "";
        selectedTsSet.forEach(ts => {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = "preferred_slots";
            input.value = new Date(ts).toISOString();
            hiddenInputsWrap.appendChild(input);
        });
        // Каждый раз, когда меняется выбор, обновляем цифры на кнопках дней
        updateDayBadges();
    }

    /**
     * СЧЕТЧИК ВЫБРАННЫХ СЛОТОВ: Функция обновления счетчиков (бейджей) на кнопках дней
     */
    function updateDayBadges() {
        Object.keys(cachedSlotsByDay).forEach(day => {
            const btn = daysRow.querySelector(`button[data-value="${day}"]`);
            if (!btn) return;

            // Считаем сколько слотов этого дня есть в selectedTsSet
            const count = cachedSlotsByDay[day].filter(iso => {
                const ts = toTimestamp(iso);
                return selectedTsSet.has(ts);
            }).length;

            // Ищем или создаем элемент бейджа
            let badge = btn.querySelector(".ts-badge");

            if (count > 0) {
                if (!badge) {
                    // ПОЯВЛЕНИЕ - используем кастомную анимацию для беэджа из custom.css
                    badge = document.createElement("span");
                    badge.className = "ts-badge ts-badge-animate absolute -top-1 -right-1 flex items-center justify-center w-5 h-5 bg-pink-500 text-white text-[10px] font-bold rounded-full border-2 border-white";
                    btn.classList.add("relative"); // Чтобы позиционировать бейдж
                    btn.appendChild(badge);
                }

                // ОБНОВЛЕНИЕ ЦИФРЫ - используем кастомную анимацию для беэджа из custom.css
                if (badge.textContent !== String(count)) {
                    badge.textContent = count;
                    badge.classList.remove("ts-badge-animate");
                    void badge.offsetWidth;
                    badge.classList.add("ts-badge-animate");
                }
            } else if (badge && !badge.classList.contains("ts-badge-out")) {
                // ПЛАВНОЕ УДАЛЕНИЕ - используем кастомную анимацию для беэджа из custom.css
                badge.classList.remove("ts-badge-animate");
                badge.classList.add("ts-badge-out");

                // Ждем окончания анимации (200ms) и только потом удаляем из DOM
                badge.addEventListener("animationend", () => {
                    badge.remove();
                }, { once: true });
            }
        });
    }

    fetch(apiUrl, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
    })
    .then(r => r.json())
    .then(data => {
        cachedSlotsByDay = data.slots; // Сохраняем для пересчета
        renderDaysAndSlots({
            slotsByDay: data.slots,
            // ВАЖНО: Передаем текущее время пользователя (nowIso) из его профиля а не сервера, чтоб потом
            // деактивировать слоты в прошлом (делаем недоступным к выбору)
            nowIso: data.now_iso,
        });
    });

    /**
     * Рендер дней + логика переключения
     */

    // nowIso: Передаем текущее время пользователя из его профиля а не сервера, чтоб потом деактивировать слоты
    // в прошлом (делаем недоступным к выбору)
    function renderDaysAndSlots({
        slotsByDay,
        nowIso
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
            renderSlotsForDay(slotsByDay[day], nowIso);
        }

        daysRow.innerHTML = "";

        // --- КНОПКИ С ДНЯМИ ---
        days.forEach(day => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.dataset.value = day;
            btn.className = dayBtnClass + " relative"; // Добавили relative (важно с пробелом в начале) для бейджа с счетчиком выбранных слотов

            const { weekday, dayMonth } = formatDayLabel(day);

            btn.innerHTML = `
                <div class="text-base font-bold">${weekday}</div>
                <div class="text-xs">${dayMonth}</div>
            `;

            btn.addEventListener("click", () => setActiveDay(day));
            daysRow.appendChild(btn);
        });

        // Первичная активация - текущий день активен по умолчанию
        setActiveDay(days[0]);
        // Инициализация бейджей со счетчиком при первой загрузке
        updateDayBadges();
    }

    /**
     * Рендер слотов конкретного дня
     */

    // nowIso: Передаем текущее время пользователя из его профиля а не сервера, чтоб потом деактивировать слоты
    // в прошлом (делаем недоступным к выбору)
    function renderSlotsForDay(slots, nowIso) {
        slotsGrid.innerHTML = "";

        slots.forEach(isoString => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.dataset.value = isoString;
            btn.textContent = formatTimeLabel(isoString);

            // Тут добавляем стиль, чтобы слоты выделялись на сером фоне
            // Также добавляем transition для плавности наведения
            btn.className = slotBtnClass + " border border-gray-200 transition-all duration-200 shadow-sm";

            const ts = toTimestamp(isoString);

            // Тут выделение НЕ доступных слотов в прошлом
            if (isoString <= nowIso) {
                btn.disabled = true;
                btn.classList.add(
                    "bg-gray-100",
                    "text-gray-400",
                    "line-through",
                    "cursor-not-allowed"
                );
            // Тут легкое выделение при наведении на еще НЕ выбранные слоты
            } else {
                btn.classList.add(
                    "hover:bg-indigo-100",
                    "hover:border-indigo-100",
                    "text-gray-700"
                );
            }

            // Тут стиль при выборе слота и при снятии выбора со слота
            btn.addEventListener("click", () => {
                if (btn.disabled || ts === null) return;

                if (selectedTsSet.has(ts)) {
                    selectedTsSet.delete(ts);

                    btn.classList.remove(
                        "bg-indigo-500",
                        "text-white",
                        "border-indigo-500",
                        "hover:bg-indigo-900"
                    );
                    btn.classList.add(
                        "hover:bg-indigo-50",
                        "hover:border-indigo-300"
                    );

                } else {
                    selectedTsSet.add(ts);
                    btn.classList.remove(
                        "hover:bg-indigo-50",
                        "hover:border-indigo-300"
                    );
                    btn.classList.add(
                        "bg-indigo-500",
                        "text-white",
                        "border-indigo-500",
                        "hover:bg-indigo-900"
                    );
                }
                syncHiddenInputs(); // Тут вызовется updateDayBadges (бейджей со счетчиком)
            });

            slotsGrid.appendChild(btn);
        });
    }
}
