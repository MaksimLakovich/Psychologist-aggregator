import { pluralizeRu } from "../utils/pluralize_ru.js";

let psychologists = [];
let currentOffset = 0;
const PAGE_SIZE = 10;
let selectedPsychologistId = null;


// Вспомогательная функция для хранения состояния страницы выбора (при обновлении браузер)
function isPageReload() {
    const nav = performance.getEntriesByType("navigation")[0];
    return nav && nav.type === "reload";
}

export function initPsychologistsChoice() {
    fetchPsychologists();
    initNavigation();
}


// Вспомогательная функция для кнопки СВЕРНУТЬ / РАЗВЕРНУТЬ (биография)
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


// Вспомогательная функция для кнопки СВЕРНУТЬ / РАЗВЕРНУТЬ (образование)
window.toggleEducation = function (btn) {
    const list = btn.previousElementSibling;
    if (!list) return;

    const isCollapsed = list.dataset.collapsed === "true";

    list.dataset.collapsed = String(!isCollapsed);
    btn.textContent = isCollapsed ? "Показать меньше" : "Показать больше";
};


// Вспомогательная функция для автоматической прокрутки к началу страницы при переключении между карточками психологов
function scrollToTopThen(callback) {
    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });

    // Ждем пока автоматический scroll вверх реально завершится
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


// ===== ШАГ 1: ЗАГРУЗКА ДАННЫХ =====
function fetchPsychologists() {
    fetch("/aggregator/api/match-psychologists/")
        .then(response => response.json())

        .then(data => {
            psychologists = data.items || [];
            if (!psychologists.length) return;

            let selectedId = null;

            if (isPageReload()) {
                selectedId = sessionStorage.getItem("selectedPsychologistId");
            }

            const selected =
                psychologists.find(ps => String(ps.id) === selectedId) ||
                psychologists[0];

            selectedPsychologistId = selected.id;

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

    // 6) Убираем копейки
    const priceValue = Number(ps.price.value).toFixed(0);


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

                    <!-- Nearest slot (stub) -->
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
                                    20 декабря в 21:00
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
                        <p class="text-lg text-gray-700 leading-relaxed overflow-hidden transition-all mt-2">
                            Часовой пояс: ${ps.timezone || "не указан"}
                        </p>
                    </div>

                </div>
            </div>

            <!-- ========== КНОПКА + ЮРИДИЧЕСКИЙ ТЕКСТ ========== -->
            <div class="pt-6 pb-16 flex justify-center">
                <div class="w-full max-w-md text-center">
                    <p class="mt-0 text-xs text-gray-500 leading-relaxed">
                        Нажимая кнопку, вы подтверждаете, что ознакомлены и согласны с договором
                        оказания услуг и даёте согласие на обработку персональных данных психологу
                    </p>
                    <button
                        type="submit"
                        class="mt-6 w-full px-10 py-3.5 rounded-xl bg-indigo-700 text-xl text-white font-medium
                               hover:bg-indigo-900 transition shadow"
                    >
                        Выбрать время сессии
                    </button>
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


// МОДАЛКА
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
