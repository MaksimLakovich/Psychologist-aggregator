import { pluralizeRu } from "../utils/pluralize_ru.js";

// Глобальное состояние страницы (список психологов + пагинация + выбранный психолог)
let psychologists = [];
let currentOffset = 0;
const PAGE_SIZE = 10;
let selectedPsychologistId = null;


/* ============================================================================
 * ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
 * ========================================================================== */


// 1) Функция для хранения состояния страницы выбора (при обновлении браузер)
// Проверяем, была ли страница перезагружена (для восстановления выбранного психолога)
function isPageReload() {
    const nav = performance.getEntriesByType("navigation")[0];
    return nav && nav.type === "reload";
}

// 2) Функция для кнопки СВЕРНУТЬ / РАЗВЕРНУТЬ (биография)
window.toggleBiography = function (btn) {
    const wrapper = btn.previousElementSibling;
    if (!wrapper) return;

    const text = wrapper.querySelector(".biography-text");
    const fade = wrapper.querySelector(".biography-fade");

    if (!text) return;

    const isCollapsed = text.dataset.collapsed === "true";

    text.dataset.collapsed = String(!isCollapsed);
    btn.textContent = isCollapsed ? "Показать меньше" : "Показать больше";

    if (fade) {
        fade.style.display = isCollapsed ? "none" : "block";
    }
};

// 3) Функция для кнопки СВЕРНУТЬ / РАЗВЕРНУТЬ (образование)
window.toggleEducation = function (btn) {
    const list = btn.previousElementSibling;
    if (!list) return;

    const isCollapsed = list.dataset.collapsed === "true";

    list.dataset.collapsed = String(!isCollapsed);
    btn.textContent = isCollapsed ? "Показать меньше" : "Показать больше";
};

// 4) Функция для автоматической прокрутки к началу страницы при переключении между карточками специалистов
// Плавно скроллим наверх и ждём завершения скролла, затем выполняем callback
function scrollToTopThen(callback) {
    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });

    // ждем пока автоматический scroll вверх реально завершится
    let lastY = window.scrollY;
    let sameCount = 0;

    const check = () => {
        const currentY = window.scrollY;

        if (currentY === lastY) {
            sameCount += 1;
        } else {
            sameCount = 0;
            lastY = currentY;
        }

        // scroll стабилизировался
        if (sameCount >= 3) {
            callback();
        } else {
            requestAnimationFrame(check);
        }
    };

    requestAnimationFrame(check);
}

// 5) Функция для преобразования слота в Date (берем start_iso или day+start_time)
function getSlotDateObj(slot) {
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

// 6) Функция для форматирования даты/времени/день недели в TZ клиента
function formatSlotParts(slot, timeZone) {
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

// 7) Функция для форматирование СЛОТА под "31 января в 05:00" в блоке "БЛИЖАЙШЕЕ ВРЕМЯ"
function formatNearestSlot(slot, timeZone) {
    const parts = formatSlotParts(slot, timeZone);
    if (!parts) return null;
    return `${parts.datePart} в ${parts.timePart} (${parts.weekdayShort})`;
}

// 8) Функция для группировки СЛОТОВ по ДНЯМ для вывода в блоке РАСПИСАНИЕ
function groupScheduleByDay(schedule = []) {
    const groups = {};
    schedule.forEach(slot => {
        const day = slot.day;
        if (!day) return;
        if (!groups[day]) groups[day] = [];
        groups[day].push(slot);
    });
    return groups;
}

// 9) Функция для генерации ключа слота (нужен для сравнения выбранного слота)
function getSlotKey(slot) {
    return slot.start_iso || `${slot.day}T${slot.start_time}`;
}

// 10) Возвращаем CSS‑класс кнопки слота в зависимости от выбранности
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

// 11) Применяем визуальное состояние к кнопке слота
function applySlotButtonState(btn, isSelected) {
    btn.className = getSlotButtonClass(isSelected);
}

// 12) Рендерим HTML блока "Расписание" (группировка по дням + кнопки слотов)
function renderScheduleList(schedule = [], selectedSlotKey = null, daysToShow = null) {
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
                const className = getSlotButtonClass(isSelected);

                return `
                    <button
                        type="button"
                        class="${className}"
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

// 13) Обновляем строку "Ближайшая запись"
function updateNearestSlotUI(nearestSlotText) {
    const nearestSlotEl = document.getElementById("ps-nearest-slot");
    if (!nearestSlotEl) return;

    nearestSlotEl.textContent = nearestSlotText || "Нет доступных слотов";
}

// 14) Обновляем блок расписания
function updateScheduleUI(schedule, selectedSlotKey = null, daysToShow = null) {
    const scheduleEl = document.getElementById("psychologist-schedule-list");
    if (!scheduleEl) return;
    scheduleEl.innerHTML = renderScheduleList(schedule, selectedSlotKey, daysToShow);
}

// 15) Функция для кнопки СВЕРНУТЬ / РАЗВЕРНУТЬ (расписание - ДНИ / СЛОТЫ)
function createScheduleToggleButton() {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "mt-3 italic text-sm font-medium text-indigo-500 hover:text-indigo-900";
    btn.dataset.state = "collapsed";
    btn.textContent = "Показать больше";
    return btn;
}

function updateScheduleToggleButton(btn, isExpanded) {
    btn.dataset.state = isExpanded ? "expanded" : "collapsed";
    btn.textContent = isExpanded ? "Показать меньше" : "Показать больше";
}

// 16) Ключ в sessionStorage для выбранного слота (переход на оплату)
const SELECTED_APPOINTMENT_SLOT_KEY = "selectedAppointmentSlot";

// 17) Сохраняем выбранный слот в sessionStorage (для страницы оплаты)
function setSelectedAppointmentSlot(psId, slot) {
    if (!slot) {
        sessionStorage.removeItem(SELECTED_APPOINTMENT_SLOT_KEY);
        return;
    }
    sessionStorage.setItem(
        SELECTED_APPOINTMENT_SLOT_KEY,
        JSON.stringify({
            psychologistId: String(psId),
            slot,
        })
    );
}

// 18) Функция для формата выбранного слота для подписи на кнопке ("Выбрать 11 февраля 10:00")
function formatSelectedSlotLabel(slot, timeZone) {
    const parts = formatSlotParts(slot, timeZone);
    if (!parts) return null;
    return `${parts.datePart} ${parts.timePart}`;
}

// 19) Функция для управления активностью и формирования подписи в КНОПКЕ: "Выбрать время сессии"
function updateChooseButton(selectedSlotLabel) {
    const btn = document.querySelector("[data-choose-session-btn]");
    if (!btn) return;
    if (selectedSlotLabel) {
        btn.disabled = false;
        btn.textContent = `Выбрать ${selectedSlotLabel}`;
        btn.classList.remove("bg-gray-300", "text-gray-500", "cursor-not-allowed");
        btn.classList.add("bg-indigo-500", "text-white", "hover:bg-indigo-900");
        updatePaymentStepLink(true);
    } else {
        btn.disabled = true;
        btn.textContent = "Выбрать время сессии";
        btn.classList.add("bg-gray-300", "text-gray-500", "cursor-not-allowed");
        btn.classList.remove("bg-indigo-500", "text-white", "hover:bg-indigo-900");
        updatePaymentStepLink(false);
    }
}

// 20) Функция для управления АКТИВНО/НЕАКТИВНО в блоке "ШАГИ" чтоб нельзя было перейти на страницу "Запись" без выбранного слота
function updatePaymentStepLink(isEnabled) {
    const link = document.querySelector("[data-payment-step-link]");
    if (!link) return;

    if (!link.dataset.href) {
        link.dataset.href = link.getAttribute("href") || "";
    }

    if (isEnabled) {
        link.setAttribute("href", link.dataset.href);
        link.classList.remove("pointer-events-none", "opacity-50");
        link.setAttribute("aria-disabled", "false");
    } else {
        link.setAttribute("href", "#");
        link.classList.add("pointer-events-none", "opacity-50");
        link.setAttribute("aria-disabled", "true");
    }
}


/* ============================================================================
 * ИНИЦИАЛИЗАЦИЯ
 * ========================================================================== */


export function initPsychologistsChoice() {
    // При заходе на страницу сбрасываем выбранный слот и блокируем переход на оплату
    sessionStorage.removeItem(SELECTED_APPOINTMENT_SLOT_KEY);
    updatePaymentStepLink(false);
    fetchPsychologists();
    initNavigation();
}


// ===== ШАГ 1: ЗАГРУЗКА ДАННЫХ (получаем список психологов по фильтрам) =====
function fetchPsychologists() {
    fetch("/aggregator/api/match-psychologists/")
        .then(response => response.json())

        .then(data => {
            psychologists = data.items || [];
            if (!psychologists.length) return;

            // Если пришли после новой/повторной фильтрации/подбора - то сбрасываем выбранного ранее психолога
            const cardContainer = document.getElementById("psychologist-card");
            const shouldReset = cardContainer?.dataset.resetChoice === "1";
            if (shouldReset) {
                sessionStorage.removeItem("selectedPsychologistId");
                cardContainer.dataset.resetChoice = "0";
            }

            // В остальных случаях пытаемся восстановить последний выбранный психолог
            let selectedId = sessionStorage.getItem("selectedPsychologistId");

            const selected =
                psychologists.find(ps => String(ps.id) === selectedId) ||
                psychologists[0];

            selectedPsychologistId = selected.id;
            // Синхронизируем выбранного психолога с sessionStorage (важно при новом подборе)
            sessionStorage.setItem("selectedPsychologistId", selectedPsychologistId);

            renderAvatars();

            scrollToTopThen(() => {
                renderPsychologistCard(selected);
                initStickyHeaderBehavior();
            });
        })

        .catch(err => {
            console.error("Ошибка загрузки психологов:", err);
        });
}


// ===== ШАГ 2: РЕНДЕР АВАТАРОВ =====
function renderAvatars() {
    const container = document.getElementById("avatar-group");
    if (!container) return;

    const baseAvatarClass =
        container.dataset.avatarClass || "";

    container.innerHTML = "";

    const pageItems = psychologists.slice(
        currentOffset,
        currentOffset + PAGE_SIZE
    );

    pageItems.forEach(ps => {
        const img = document.createElement("img");

        img.src = ps.photo || "/static/images/menu/user-circle.svg";
        img.alt = "Психолог";

        img.className = `
            ${baseAvatarClass}
            cursor-pointer
            transition-all duration-200 ease-out
            ${ps.id === selectedPsychologistId
                ? "ring-4 ring-indigo-500 scale-105"
                : "ring-2 ring-transparent hover:ring-indigo-300 hover:scale-105"}
        `;

        img.addEventListener("click", () => {
            selectedPsychologistId = ps.id;

            sessionStorage.setItem(
                "selectedPsychologistId",
                selectedPsychologistId
            );

            renderAvatars();

            scrollToTopThen(() => {
                renderPsychologistCard(ps);
                initStickyHeaderBehavior();
            });

        });

        container.appendChild(img);
    });

    updateNavigationState();
}


// ===== НАВИГАЦИЯ (кнопки ВЛЕВО / ВПРАВО) =====
function initNavigation() {
    const prevBtn = document.getElementById("ps-prev");
    const nextBtn = document.getElementById("ps-next");

    if (prevBtn) {
        prevBtn.addEventListener("click", () => {
            if (currentOffset > 0) {
                currentOffset -= PAGE_SIZE;
                renderAvatars();
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener("click", () => {
            if (currentOffset + PAGE_SIZE < psychologists.length) {
                currentOffset += PAGE_SIZE;
                renderAvatars();
            }
        });
    }
}

function updateNavigationState() {
    const prevBtn = document.getElementById("ps-prev");
    const nextBtn = document.getElementById("ps-next");

    if (prevBtn) {
        prevBtn.disabled = currentOffset === 0;
    }

    if (nextBtn) {
        nextBtn.disabled = currentOffset + PAGE_SIZE >= psychologists.length;
    }
}


// ===== ШАГ 3: КАРТОЧКА ПСИХОЛОГА =====
function renderPsychologistCard(ps) {
    const container = document.getElementById("psychologist-card");
    if (!container || !ps) return;

    const staticUrl = container.dataset.staticUrl;
    // Получаем из Django проброшенный timezone в dataset для использования в JS при рендере тут карточки специалиста
    const clientTimezone = container.dataset.clientTimezone || "не указан";
    // Получаем URL из атрибута в home_client_choice_psychologist.html (data-back-url="{% url 'core:personal-questions' %}")
    const backUrl = container.dataset.backUrl; // ПОЛУЧАЕМ НАШ URL ИЗ АТРИБУТА

    // HELPERS

    // 1) Логика для отображения и сортировки Education: сначала с year_end, потом "в процессе"
    const renderEducations = (educations = []) => {
        if (!educations.length) {
            return `<p class="text-gray-500 text-sm">Информация об образовании не указана</p>`;
        }

        const sorted = [...educations].sort((a, b) => {
            if (!a.year_end) return 1;
            if (!b.year_end) return -1;
            return b.year_end - a.year_end;
        });

        const hasMoreThanTwo = sorted.length > 2;

        return `
            <ul
                class="relative education-list mt-2 space-y-3"
                data-collapsed="true"
            >
                ${sorted.map(edu => `

                    <li class="text-lg text-gray-700 leading-relaxed transition-all">
                        <div class="font-medium">
                            ${edu.year_end ?? "в процессе"}
                        </div>
                        <div>
                            ${edu.institution}
                            ${edu.specialisation ? `, ${edu.specialisation}` : ""}
                        </div>
                    </li>

                `).join("")}
            </ul>

            ${hasMoreThanTwo ? `
                <button
                    type="button"
                    class="mt-3 italic text-sm font-medium text-indigo-500 hover:text-indigo-900"
                    onclick="toggleEducation(this)"
                >
                    Показать больше
                </button>
            ` : ""}
        `;
    };

    // 2) Логика для отображения БЕЙДЖЕВ в КОЛОНКУ (например, Topics)
    const COLOR_MAP = {
        indigo: "bg-indigo-200 text-indigo-700",
        green: "bg-green-200 text-green-700",
    };

    const renderBadges = (items = [], color = "indigo", direction = "row") => {
        if (!items.length) {
            return `<p class="text-gray-500 text-sm">Не указано</p>`;
        }

        // Это задает в бэйджах отображение значений в колонку (один под одним)
        const directionClass =
            direction === "column"
                ? "flex-col items-start"
                : "flex-wrap";

        return `
            <div class="mt-3 flex flex-wrap gap-2 ${directionClass}">
                ${items.map(item => `
                    <span class="rounded-full px-3 py-1 text-base font-medium tracking-wider ${COLOR_MAP[color]}">
                        ${item.name}
                    </span>
                `).join("")}
            </div>
        `;
    };

    // 3) Логика для отображения СПИСКА в КОЛОНКУ (например, Methods)
    const renderVerticalList = (items = []) => {
        if (!items.length) {
            return `<p class="text-gray-500 text-sm">Не указано</p>`;
        }

        return `
            <ul class="relative mt-2 space-y-2">
                ${items.map(item => `
                    <li class="flex items-center gap-2 text-lg text-gray-700">
                        <span class="h-2 w-2 rounded-full bg-indigo-400 flex-shrink-0"></span>
                        <span>${item.name}</span>
                    </li>
                `).join("")}
            </ul>
        `;
    };

    // 4) Подключаю pluralize_ru.js и рассчитываем правильное окончание для слова ГОД
    const word = pluralizeRu(
        ps.work_experience,
        "год",
        "года",
        "лет"
    );

    // 5) Логика отображения PRICE в зависимости от "individual/couple"
    const isCoupleSession = ps.session_type === "couple";

    const sessionLabel = isCoupleSession
        ? "Парная сессия · 1,5 часа"
        : "Индивидуальная сессия · 50 минут";

    // 6) Убираем копейки в стоимости сессии
    const priceValue = Number(ps.price.value).toFixed(0);

    // 7) Подгружаем РАСПИСАНИЕ и БЛИЖАЙШЕЕ ВРЕМЯ для выбранного специалиста
    const currentPsId = ps.id;
    container.dataset.psId = String(currentPsId);
    let selectedSlotKey = null;

    // Сбрасываем выбор при переключении на другого специалиста
    updateChooseButton(null);
    setSelectedAppointmentSlot(currentPsId, null);

    fetch(`/users/api/psychologists/${currentPsId}/schedule/`)
        .then(response => response.json())
        .then(data => {
            // Защита от гонок: если карточка уже переключена на другого психолога - игнорируем
            if (container.dataset.psId !== String(currentPsId)) return;

            if (!data || data.status !== "ok") {
                updateNearestSlotUI("Нет доступных слотов");
                updateScheduleUI([], null);
                updateChooseButton(null);
                return;
            }

            const schedule = data.schedule || [];
            const nearestText = formatNearestSlot(data.nearest_slot, clientTimezone);
            updateNearestSlotUI(nearestText || "Нет доступных слотов");

            const grouped = groupScheduleByDay(schedule);
            const allDays = Object.keys(grouped).sort();
            const defaultVisibleDays = 3;
            let isExpanded = false;

            updateScheduleUI(schedule, selectedSlotKey, defaultVisibleDays);

            const scheduleEl = document.getElementById("psychologist-schedule-list");
            if (scheduleEl) {
                // Кнопка "Показать больше/меньше" для расписания
                let toggleBtn = document.getElementById("schedule-toggle-btn");
                if (toggleBtn) {
                    toggleBtn.remove();
                }

                if (allDays.length > defaultVisibleDays) {
                    toggleBtn = createScheduleToggleButton();
                    toggleBtn.id = "schedule-toggle-btn";
                    scheduleEl.after(toggleBtn);

                    toggleBtn.addEventListener("click", () => {
                        isExpanded = !isExpanded;
                        updateScheduleToggleButton(toggleBtn, isExpanded);
                        updateScheduleUI(
                            schedule,
                            selectedSlotKey,
                            isExpanded ? null : defaultVisibleDays
                        );
                    });
                }

                scheduleEl.onclick = event => {
                    const btn = event.target.closest("button[data-slot-key]");
                    if (!btn) return;

                    const newKey = btn.dataset.slotKey;
                    if (!newKey) return;

                    selectedSlotKey = newKey;

                    scheduleEl.querySelectorAll("button[data-slot-key]").forEach(el => {
                        applySlotButtonState(el, false);
                    });

                    applySlotButtonState(btn, true);

                    const slotObj = schedule.find(slot => getSlotKey(slot) === newKey);
                    updateChooseButton(formatSelectedSlotLabel(slotObj, clientTimezone));
                    setSelectedAppointmentSlot(currentPsId, slotObj);
                };
            }
        })
        .catch(() => {
            if (container.dataset.psId !== String(currentPsId)) return;
            updateNearestSlotUI("Нет доступных слотов");
            updateScheduleUI([], null);
            updateChooseButton(null);
        });

    // HTML-ШАБЛОН
    container.innerHTML = `
        <div class="mt-8 rounded-2xl border-2 border-indigo-100 bg-indigo-50 shadow-2xl shadow-indigo-300">

            <div class="relative grid grid-cols-1 md:grid-cols-12 gap-6 p-6 pt-16">

                <!-- LEFT COLUMN -->
                <div
                    class="md:col-span-4 flex flex-col items-center md:sticky self-start"
                    style="top: var(--choice-header-offset);"
                >
                    <img
                        src="${ps.photo}"
                        alt="Фото психолога"
                        class="
                            h-64 w-64 rounded-full object-cover cursor-pointer transition-all
                            duration-300 ease-out border-1 border-transparent hover:border-indigo-300
                            hover:scale-[1.01] hover:shadow-2xl
                        "
                    />
                    <!-- SLOT: сюда будет переезжать Header + Price при скролле страницы вниз/вверх-->
                    <div
                        id="ps-left-companion"
                        class="mt-6 w-full space-y-4 transition-all duration-300"
                    ></div>
                </div>

                <!-- RIGHT COLUMN -->
                <div class="md:col-span-8 space-y-6 md:pl-6 md:pr-6 lg:pl-8 lg:pr-12">

                    <!-- Оборачиваем Header + Price чтоб потом можно было перенести под фото при скролле -->
                    <div id="ps-main-header">

                        <!-- Header -->
                        <div class="pb-4">
                            <h2 class="text-3xl font-semibold text-gray-900 pb-2">
                                ${ps.full_name}
                            </h2>
                            <div class="inline-flex items-center gap-3">
                                <div class="inline-flex items-center gap-2 rounded-full bg-indigo-100 px-3 py-2 mt-3 hover:bg-indigo-200 transition">
                                    <img
                                        src="${staticUrl}images/psychologist_profile/goal-svgrepo-com.svg"
                                        alt="goal_icon"
                                    />
                                    <span class="text-lg text-gray-700 font-medium">
                                        ${ps.rating} из 10
                                    </span>
                                </div>
                                <div class="inline-flex items-center gap-2 rounded-full bg-indigo-100 px-3 py-2 mt-3 hover:bg-indigo-200 transition">
                                    <img
                                        src="${staticUrl}images/psychologist_profile/seal-check.svg"
                                        alt="check_icon"
                                    />
                                    <span class="text-lg text-gray-700 font-medium">
                                        ${ps.work_experience
                                            ? `Опыт ${ps.work_experience} ${word}`
                                            : "Опыт не указан"}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- Price -->
                        <div class="rounded-xl bg-transparent p-0">
                            <p class="text-lg font-medium text-gray-700 dark:text-gray-200">
                                ${sessionLabel}
                            </p>
                            <p class="mt-0 text-xl font-semibold text-gray-700">
                                ${priceValue} ₽
                            </p>
                        </div>

                    </div>

                    <!-- Nearest slot -->
                    <div class="pb-7">
                        <div class="gap-0 rounded-xl bg-transparent p-0 pb-2">
                            <div class="inline-flex items-center gap-1">
                                <p
                                    class="text-lg font-medium text-gray-700 dark:text-gray-200"
                                >
                                    Ближайшая запись
                                </p>
                                <p
                                    class="mt-0 text-lg font-semibold text-indigo-700 hover:text-indigo-800 transition cursor-pointer"
                                    onclick="document.getElementById('psychologist-schedule')?.scrollIntoView({behavior: 'smooth'})"
                                >
                                    <span id="ps-nearest-slot">Загружаем...</span>
                                </p>
                            </div>
                        </div>
                        <button
                            type="button"
                            class="rounded-xl bg-indigo-500 border-indigo-900 px-6 py-2.5 text-white text-lg font-medium hover:bg-indigo-900 transition"
                            onclick="document.getElementById('psychologist-schedule')?.scrollIntoView({behavior: 'smooth'})"
                        >
                            Выбрать время сессии
                        </button>
                    </div>

                    <!-- Biography -->
                    <div class="pb-7">
                        <h3 class="text-xl font-semibold text-gray-900">
                            О специалисте
                        </h3>
                        <div class="relative mt-2">
                            <p
                                class="biography-text text-lg text-gray-700 leading-relaxed overflow-hidden transition-all"
                                data-collapsed="true"
                            >
                                ${ps.biography || "Описание специалиста не указано"}
                            </p>
                            <div class="biography-fade pointer-events-none"></div>
                        </div>
                        <button
                            type="button"
                            class="mt-4 italic text-sm font-medium text-indigo-500 hover:text-indigo-900"
                            onclick="toggleBiography(this)"
                        >
                            Показать больше
                        </button>
                    </div>

                    <!-- Education -->
                    <div class="pb-7">
                        <h3 class="text-xl font-semibold text-gray-900">
                            Образование
                        </h3>
                        ${renderEducations(ps.educations)}
                    </div>

                    <!-- Methods -->
                    <div class="pb-7">

                        <div class="flex inline-flex items-center gap-2">
                            <h3 class="text-xl font-semibold text-gray-900">
                                Методы терапии
                            </h3>
                            <button
                                type="button"
                                class="text-sm font-medium text-indigo-500 hover:text-indigo-900 transition"
                                onclick="openMethodsInfoModal(${ps.id})"
                            >
                                <img
                                    src="${staticUrl}images/psychologist_profile/info.svg"
                                    alt="info_icon"
                                />
                            </button>
                        </div>

                        ${renderVerticalList(ps.methods)}

                    </div>

                    <!-- Topics -->
                    <div class="pb-7">
                        <h3 class="text-xl font-semibold text-gray-900">
                            Работает с темами вашей анкеты
                        </h3>
                        ${renderBadges(ps.matched_topics, "indigo", "column")}
                    </div>

                    <!-- Schedule -->
                    <div
                        id="psychologist-schedule"
                        class="pb-7"
                    >
                        <h3 class="text-xl font-semibold text-gray-900">
                            Расписание
                        </h3>
                        <div class="flex items-center gap-1 mt-2">
                            <img
                                src="${staticUrl}images/psychologist_profile/time-zone.svg"
                                alt="time_icon"
                                aria-hidden="true"
                                class="w-5 h-5"
                            />
                            <p class="text-lg text-gray-700 leading-relaxed">
                                Часовой пояс: ${clientTimezone}
                            </p>
                        </div>
                        <div id="psychologist-schedule-list" class="mt-2"></div>
                    </div>

                </div>
            </div>

            <!-- ========== КНОПКА + ЮРИДИЧЕСКИЙ ТЕКСТ ========== -->
            <div class="pt-6 pb-16 flex justify-center">
                <div class="w-full max-w-md text-center">
                    <p class="mt-0 text-xs text-gray-500 leading-relaxed">
                        Нажимая кнопку, вы подтверждаете, что ознакомлены и согласны с
                        <button
                                type="button"
                                class="text-xs font-medium text-indigo-500 hover:text-indigo-900 transition"
                                onclick="openServiceAgreementModal(${ps.id})"
                            >
                            договором оказания услуг
                        </button>
                        и даёте согласие на обработку персональных данных психологу
                    </p>
                    <button
                        type="submit"
                        class="mt-6 w-full px-10 py-3.5 rounded-xl bg-gray-300 text-xl text-gray-500
                            font-extrabold tracking-wide cursor-not-allowed transition shadow"
                        data-choose-session-btn
                        disabled
                    >
                        Выбрать время сессии
                    </button>
                    <div class="pt-6">
                        <a href="${backUrl}"
                           class="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-indigo-200 text-xl text-white font-extrabold tracking-wide hover:bg-indigo-300 transition">
                            Назад
                        </a>
                    </div>
                </div>
            </div>

        </div>
    `;
}


// ===== STICKY COMPANION: перенос "Header + Price" под АВАТАР при скролле карточки клиента вниз =====
let headerObserver = null;
let stickyHeaderClone = null;

function initStickyHeaderBehavior() {
    const header = document.getElementById("ps-main-header");
    const leftSlot = document.getElementById("ps-left-companion");

    if (!header || !leftSlot) return;

    // 1) ОТКЛЮЧАЕМ старый observer
    if (headerObserver) {
        headerObserver.disconnect();
        headerObserver = null;
    }

    // 2) УДАЛЯЕМ старый clone
    if (stickyHeaderClone) {
        stickyHeaderClone.remove();
        stickyHeaderClone = null;
    }

    // 3) Создаем clone ВСЕГДА заново
    if (!stickyHeaderClone) {
        stickyHeaderClone = header.cloneNode(true);
        stickyHeaderClone.id = "ps-main-header-clone";
        stickyHeaderClone.classList.add(
            "ps-header-clone",          // ДОБАВЛЯЮ кастомный стиль для clone под ФОТО ПСИХОЛОГА
            "opacity-0",
            "pointer-events-none",
            "transition-opacity",
            "duration-300"
        );
        leftSlot.appendChild(stickyHeaderClone);
    }

    if (headerObserver) {
        headerObserver.disconnect();
    }

    headerObserver = new IntersectionObserver(
        ([entry]) => {
            if (!entry.isIntersecting) {
                // показываем clone
                stickyHeaderClone.classList.remove("opacity-0", "pointer-events-none");
                stickyHeaderClone.classList.add("opacity-100");
            } else {
                // скрываем clone
                stickyHeaderClone.classList.add("opacity-0", "pointer-events-none");
                stickyHeaderClone.classList.remove("opacity-100");
            }
        },
        {
            root: null,
            threshold: 0,
            rootMargin: "-80px 0px 0px 0px",
        }
    );

    headerObserver.observe(header);
}


// МОДАЛКА ДЛЯ ОТОБРАЖАНЕИЯ ОПИСАНИЯ МЕТОДОВ
window.openMethodsInfoModal = function (psychologistId) {
    const ps = psychologists.find(p => p.id === psychologistId);
    if (!ps || !ps.methods?.length) return;

    const content = document.getElementById("methods-info-content");
    const modal = document.getElementById("methods-info-modal");

    content.innerHTML = ps.methods.map(method => `
        <div>
            <h4 class="text-lg font-semibold text-gray-900">
                ${method.name}
            </h4>
            <p class="mt-1 text-gray-700 leading-relaxed">
                ${method.description || "Описание отсутствует"}
            </p>
        </div>
    `).join("");

    modal.classList.remove("hidden");
    modal.classList.add("flex");
};

window.closeMethodsInfoModal = function () {
    const modal = document.getElementById("methods-info-modal");
    modal.classList.add("hidden");
    modal.classList.remove("flex");
};


// МОДАЛКА ДЛЯ ОТОБРАЖАНЕИЯ ДОГОВОРА ОБ ОКАЗАНИИ УСЛУГ
window.openServiceAgreementModal = function (psychologistId) {
    const ps = psychologists.find(p => p.id === psychologistId);
    if (!ps) return;

    const modal = document.getElementById("service-agreement-modal");
    const content = document.getElementById("service-agreement-content");

    if (!modal || !content) return;

    content.innerHTML = `
        <p>
            <strong>${ps.full_name}</strong> (далее — «Психолог») разместил настоящий текст,
            являющийся публичной офертой, т.е. предложением Психолога, указанного на соответствующей
            странице сайта и в мобильных приложениях, заключить договор с любым пользователем
            (далее — «Пользователь») относительно проведения психологических консультаций онлайн.
        </p>

        <p>
            В соответствии с пунктом 3 статьи 438 Гражданского кодекса Российской Федерации
            надлежащим акцептом настоящей оферты считается последовательное осуществление Пользователем
            следующих действий:
        </p>

        <ul class="list-disc pl-5 space-y-2">
            <li>ознакомление с условиями настоящей оферты;</li>
            <li>введение регистрационных данных;</li>
            <li>нажатие кнопки «Оплатить» или аналога.</li>
        </ul>

        <p class="pt-4">
            С момента совершения указанных действий договор оказания услуг считается заключённым
            между Психологом и Пользователем.
        </p>

    `;

    modal.classList.remove("hidden");
    modal.classList.add("flex");
};

window.closeServiceAgreementModal = function () {
    const modal = document.getElementById("service-agreement-modal");
    modal.classList.add("hidden");
    modal.classList.remove("flex");
};
