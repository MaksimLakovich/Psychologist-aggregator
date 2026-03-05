import {
    applySlotButtonState,
    createScheduleToggleButton,
    formatNearestSlot,
    formatSlotParts,
    getSlotKey,
    groupScheduleByDay,
    updateNearestSlotUI,
    updateScheduleToggleButton,
    updateScheduleUI,
} from "./detail_card_schedule.js";
import {
    setSelectedAppointmentSlot,
    updateChooseButton,
} from "./detail_card_session_choice.js";

/**
 * Бизнес-смысл модуля:
 * Клиент принимает решение о записи внутри одной цельной карточки специалиста.
 * Модуль отвечает за полную отрисовку этой карточки и за "живую" часть
 * (подгрузка расписания, выбор слота, активация CTA).
 *
 * Почему это важно для бизнеса:
 * - все ключевые сигналы доверия (опыт, методы, образование, свободные слоты)
 *   клиент видит в одном экране;
 * - единый runtime снижает стоимость поддержки и риск расхождений между страницами;
 * - корректная работа CTA напрямую влияет на конверсию в запись.
 */

// Функция для формата выбранного слота для подписи на кнопке ("Выбрать 11 февраля 10:00")
function formatSelectedSlotLabel(slot, timeZone) {
    // Используем общий форматтер частей даты/времени, чтобы подпись
    // в кнопке и расписании выглядела одинаково для клиента.
    const parts = formatSlotParts(slot, timeZone);
    if (!parts) return null;
    return `${parts.datePart} ${parts.timePart}`;
}

function formatPriceAmount(value) {
    // Приводим любые входные значения цены (string/number/null) к безопасному числу.
    const parsed = Number.parseFloat(String(value));
    // Если данных нет или формат битый, в UI выводим "0", а не NaN.
    if (!Number.isFinite(parsed)) return "0";
    // Для карточки используем целые значения без копеек.
    return parsed.toFixed(0);
}

// Основной рендер карточки психолога (структура/стили)
export function renderPsychologistCard(ps, options = {}) {
    // Точка монтирования карточки. Если контейнер не найден, дальше работать нельзя.
    const container = document.getElementById("psychologist-card");
    if (!container || !ps) return;

    // Базовый static URL нужен для иконок/изображений внутри HTML-шаблона карточки.
    const staticUrl = container.dataset.staticUrl;
    // Получаем из Django проброшенный timezone в dataset для использования в JS при рендере тут карточки специалиста
    const clientTimezone = container.dataset.clientTimezone || "не указан";
    // Получаем URL из атрибута в home_client_choice_psychologist.html (data-back-url="{% url 'core:personal-questions' %}")
    const backUrl = container.dataset.backUrl; // ПОЛУЧАЕМ НАШ URL ИЗ АТРИБУТА
    // Режим определяет, какую бизнес-логику карточки применяем:
    // - matching-choice: сценарий подбора после анкеты;
    // - catalog-detail: сценарий детальной карточки из каталога.
    const renderMode = options.mode === "catalog-detail" ? "catalog-detail" : "matching-choice";
    // Тип консультации из состояния каталога (если есть) влияет на показ цены.
    const consultationType = options.consultationType === "individual" || options.consultationType === "couple"
        ? options.consultationType
        : null;
    // Поле с темами задаем опцией, чтобы один runtime поддерживал и matched_topics, и topics.
    const topicsField = typeof options.topicsField === "string" ? options.topicsField : "matched_topics";
    // Заголовок блока тем также настраивается опцией под бизнес-сценарий.
    const topicsTitle = typeof options.topicsTitle === "string"
        ? options.topicsTitle
        : "Работает с темами вашей анкеты";
    // Управляем завершающим CTA без изменения поведения matching-flow:
    // - submit: переход к следующему шагу (выбор психолога после анкеты);
    // - button: заглушка без перехода (детальная карточка из каталога).
    const chooseSessionButtonType = options.chooseSessionButtonType === "button" ? "button" : "submit";
    // В каталоге нижняя кнопка "Назад" дублирует верхний "Назад в каталог", поэтому прячем её опционально.
    const showBottomBackButton = options.showBottomBackButton !== false;

    // HELPERS

    // 1) Логика для отображения и сортировки Education: сначала с year_end, потом "в процессе"
    const renderEducations = (educations = []) => {
        // Пустой state показываем явно, чтобы клиент не думал, что блок "сломался".
        if (!educations.length) {
            return `<p class="text-gray-500 text-sm">Информация об образовании не указана</p>`;
        }

        // Вверху показываем завершенные этапы обучения с более свежим годом окончания.
        const sorted = [...educations].sort((a, b) => {
            if (!a.year_end) return 1;
            if (!b.year_end) return -1;
            return b.year_end - a.year_end;
        });

        // Если записей много, даем клиенту компактный режим с кнопкой "Показать больше".
        const hasMoreThanTwo = sorted.length > 2;

        return `
            <ul class="relative education-list mt-2 space-y-3" data-collapsed="true">
                ${sorted.map(edu => `
                    <li class="text-lg text-gray-700 leading-relaxed transition-all">
                        <div class="font-medium">${edu.year_end ?? "в процессе"}</div>
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
        // Цветовые пресеты бейджей для визуального разделения смысловых групп.
        indigo: "bg-indigo-200 text-indigo-700",
        green: "bg-green-200 text-green-700",
    };

    const renderBadges = (items = [], color = "indigo", direction = "row") => {
        // Явный fallback-текст защищает UX при пустых данных профиля.
        if (!items.length) {
            return `<p class="text-gray-500 text-sm">Не указано</p>`;
        }

        // Это задает в бэйджах отображение значений в колонку (один под одним)
        const directionClass = direction === "column" ? "flex-col items-start" : "flex-wrap";

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

    // 4) Получаем готовую подпись опыта только из backend (единая точка правды).
    // Если поле по какой-то причине отсутствует, выводим нейтральный текст.
    const experienceLabel = ps.experience_label || "Опыт не указан";

    // Валюту и суммы приводим к универсальному виду:
    // - в matching приходят ps.price.value/currency;
    // - в catalog-detail приходят price_individual/price_couples/price_currency.
    const currency = ps.price_currency || ps.price?.currency || "RUB";
    const individualPriceValue = formatPriceAmount(ps.price_individual);
    const couplePriceValue = formatPriceAmount(ps.price_couples);

    // 5) Логика отображения PRICE в зависимости от сценария:
    // - matching-choice: показываем одну цену выбранного типа (как раньше);
    // - catalog-detail: показываем цену по выбранному consultation_type или обе цены, если тип не выбран.
    let sessionPriceHtml = "";
    if (renderMode === "catalog-detail") {
        // Для каталога:
        // - если выбран фильтр консультации, показываем только релевантный ценник;
        // - если фильтра нет, показываем обе цены, чтобы клиент видел полный прайс психолога.
        if (consultationType === "individual") {
            sessionPriceHtml = `
                <div class="rounded-xl bg-transparent p-0">
                    <p class="text-lg font-medium text-gray-700 dark:text-gray-200">Индивидуальная сессия · 50 минут</p>
                    <p class="mt-0 text-xl font-semibold text-gray-700">${individualPriceValue} ${currency}</p>
                </div>
            `;
        } else if (consultationType === "couple") {
            sessionPriceHtml = `
                <div class="rounded-xl bg-transparent p-0">
                    <p class="text-lg font-medium text-gray-700 dark:text-gray-200">Парная сессия · 1,5 часа</p>
                    <p class="mt-0 text-xl font-semibold text-gray-700">${couplePriceValue} ${currency}</p>
                </div>
            `;
        } else {
            sessionPriceHtml = `
                <div class="rounded-xl bg-transparent p-0 space-y-2">
                    <div>
                        <p class="text-lg font-medium text-gray-700 dark:text-gray-200">Индивидуальная сессия · 50 минут</p>
                        <p class="mt-0 text-xl font-semibold text-gray-700">${individualPriceValue} ${currency}</p>
                    </div>
                    <div>
                        <p class="text-lg font-medium text-gray-700 dark:text-gray-200">Парная сессия · 1,5 часа</p>
                        <p class="mt-0 text-xl font-semibold text-gray-700">${couplePriceValue} ${currency}</p>
                    </div>
                </div>
            `;
        }
    } else {
        // Для matching-сценария оставляем прежнее поведение "один выбранный формат сессии".
        const isCoupleSession = ps.session_type === "couple";
        const sessionLabel = isCoupleSession
            ? "Парная сессия · 1,5 часа"
            : "Индивидуальная сессия · 50 минут";
        const priceValue = Number(ps.price.value).toFixed(0);
        sessionPriceHtml = `
            <div class="rounded-xl bg-transparent p-0">
                <p class="text-lg font-medium text-gray-700 dark:text-gray-200">
                    ${sessionLabel}
                </p>
                <p class="mt-0 text-xl font-semibold text-gray-700">
                    ${priceValue} ₽
                </p>
            </div>
        `;
    }

    // Источник тем зависит от сценария: matched_topics (подбор) или topics (каталог).
    const topics = Array.isArray(ps[topicsField]) ? ps[topicsField] : [];
    // Нижняя "Назад" управляется отдельной опцией, чтобы не дублировать UX в каталоге.
    const backButtonHtml = showBottomBackButton
        ? `
                    <div class="pt-6">
                        <a href="${backUrl}"
                           class="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-indigo-200 text-xl text-white font-extrabold tracking-wide hover:bg-indigo-300 transition">
                            Назад
                        </a>
                    </div>
        `
        : "";

    // 7) Подгружаем РАСПИСАНИЕ и БЛИЖАЙШЕЕ ВРЕМЯ для выбранного специалиста
    const currentPsId = ps.id;
    // Сохраняем id в DOM, чтобы отсекать "гонки" при быстром переключении карточек.
    container.dataset.psId = String(currentPsId);
    // Ключ выбранного слота внутри текущего расписания.
    let selectedSlotKey = null;

    // Сбрасываем выбор при переключении на другого специалиста
    updateChooseButton(null);
    setSelectedAppointmentSlot(currentPsId, null);

    // Получаем актуальное расписание психолога.
    fetch(`/users/api/psychologists/${currentPsId}/schedule/`)
        .then(response => response.json())
        .then(data => {
            // Защита от гонок: если карточка уже переключена на другого психолога - игнорируем
            if (container.dataset.psId !== String(currentPsId)) return;

            // Если API не дал корректный ответ, показываем "без слотов" и не даем перейти по CTA.
            if (!data || data.status !== "ok") {
                updateNearestSlotUI("Нет доступных слотов");
                updateScheduleUI([], null);
                updateChooseButton(null);
                return;
            }

            // Нормализуем payload расписания и ближайшего времени.
            const schedule = data.schedule || [];
            const nearestText = formatNearestSlot(data.nearest_slot, clientTimezone);
            updateNearestSlotUI(nearestText || "Нет доступных слотов");

            // Группировка по дням нужна для "Показать больше/меньше" на уровне дней, а не отдельных кнопок.
            const grouped = groupScheduleByDay(schedule);
            // Список дней в стабильном порядке для предсказуемого UX.
            const allDays = Object.keys(grouped).sort();
            // По умолчанию показываем только первые N дней, чтобы карточка не становилась слишком длинной.
            const defaultVisibleDays = 3;
            // Локальный флаг текущего состояния кнопки "Показать больше/меньше".
            let isExpanded = false;

            updateScheduleUI(schedule, selectedSlotKey, defaultVisibleDays);

            // Контейнер расписания, внутри которого делегируем все клики по слотам.
            const scheduleEl = document.getElementById("psychologist-schedule-list");
            if (!scheduleEl) return;

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
                    // Переключаем "свернуто/развернуто" только для расписания,
                    // не затрагивая другие блоки карточки.
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
                // Делегирование клика: обрабатываем только кнопки слотов.
                const btn = event.target.closest("button[data-slot-key]");
                if (!btn) return;

                const newKey = btn.dataset.slotKey;
                if (!newKey) return;

                // Фиксируем новый выбранный слот и обновляем визуальное выделение.
                selectedSlotKey = newKey;

                scheduleEl.querySelectorAll("button[data-slot-key]").forEach(el => {
                    applySlotButtonState(el, false);
                });

                applySlotButtonState(btn, true);

                // После выбора:
                // 1) обновляем подпись CTA;
                // 2) сохраняем слот в sessionStorage для следующего шага.
                const slotObj = schedule.find(slot => getSlotKey(slot) === newKey);
                updateChooseButton(formatSelectedSlotLabel(slotObj, clientTimezone));
                setSelectedAppointmentSlot(currentPsId, slotObj);
            };
        })
        .catch(() => {
            // Сетевые ошибки не должны ломать карточку: показываем контролируемый fallback UI.
            if (container.dataset.psId !== String(currentPsId)) return;
            updateNearestSlotUI("Нет доступных слотов");
            updateScheduleUI([], null);
            updateChooseButton(null);
        });

    // HTML-шаблон карточки.
    // Важно: рендерим его после запуска fetch, чтобы скелетон сразу заменился на контент,
    // а данные расписания доехали асинхронно и мягко обновили нужные зоны.
    container.innerHTML = `
        <div class="mt-8 rounded-2xl border-2 border-indigo-100 bg-indigo-50 shadow-2xl shadow-indigo-300">

            <div class="relative grid grid-cols-1 md:grid-cols-12 gap-6 p-6 pt-16">

                <!-- LEFT COLUMN -->
                <div
                    class="md:col-span-4 flex flex-col items-center md:sticky self-start"
                    style="top: var(--choice-header-offset, 1rem);"
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
                                        ${experienceLabel}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- Price -->
                        ${sessionPriceHtml}

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
                            ${topicsTitle}
                        </h3>
                        ${renderBadges(topics, "indigo", "column")}
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
                        type="${chooseSessionButtonType}"
                        class="mt-6 w-full px-10 py-3.5 rounded-xl bg-gray-300 text-xl text-gray-500 font-extrabold tracking-wide cursor-not-allowed transition shadow"
                        data-choose-session-btn
                        disabled
                    >
                        Выбрать время сессии
                    </button>
                    ${backButtonHtml}
                </div>
            </div>

        </div>
    `;
}
