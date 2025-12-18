import { pluralizeRu } from "../utils/pluralize_ru.js";

let psychologists = [];
let currentOffset = 0;
const PAGE_SIZE = 10;
let selectedPsychologistId = null;

// Вспомогательная функция для хранения состояния страницы выбора
function isPageReload() {
    const nav = performance.getEntriesByType("navigation")[0];
    return nav && nav.type === "reload";
}

export function initPsychologistsChoice() {
    fetchPsychologists();
    initNavigation();
}

// ШАГ 1: ЗАГРУЗКА ДАННЫХ
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
            renderPsychologistCard(selected);
        })

        .catch(err => {
            console.error("Ошибка загрузки психологов:", err);
        });
}

// ШАГ 2: РЕНДЕР АВАТАРОВ
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
            renderPsychologistCard(ps);
        });

        container.appendChild(img);
    });

    updateNavigationState();
}

// НАВИГАЦИЯ (кнопки ВЛЕВО / ВПРАВО)
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

// ШАГ 3: КАРТОЧКА ПСИХОЛОГА
function renderPsychologistCard(ps) {
    const container = document.getElementById("psychologist-card");
    if (!container || !ps) return;

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

        return `
            <ul class="mt-3 space-y-3">
                ${sorted.map(edu => `
                    <li class="text-gray-700">
                        <span class="font-medium">
                            ${edu.year_start}–${edu.year_end ?? "в процессе"}
                        </span>
                        · ${edu.institution}
                        ${edu.specialisation ? ` — ${edu.specialisation}` : ""}
                    </li>
                `).join("")}
            </ul>
        `;
    };

    // 2) Логика для отображения БЕЙДЖЕВ
    const COLOR_MAP = {
        indigo: "bg-indigo-100 text-indigo-700",
        green: "bg-green-100 text-green-700",
    };

    const renderBadges = (items = [], color = "indigo") => {
        if (!items.length) {
            return `<p class="text-gray-500 text-sm">Не указано</p>`;
        }

        return `
            <div class="mt-3 flex flex-wrap gap-2">
                ${items.map(item => `
                    <span class="rounded-full px-3 py-1 text-sm ${COLOR_MAP[color]}">
                        ${item.name}
                    </span>
                `).join("")}
            </div>
        `;
    };

    // 3)
    const word = pluralizeRu(
        ps.work_experience,
        "год",
        "года",
        "лет"
    );


    // HTML-ШАБЛОН
    container.innerHTML = `
        <div class="mt-8 rounded-2xl border border-gray-200 bg-white shadow-sm">

            <div class="grid grid-cols-1 md:grid-cols-12 gap-6 p-6">

                <!-- LEFT COLUMN -->
                <div class="md:col-span-3 flex justify-center">
                    <img
                        src="${ps.photo}"
                        alt="Фото психолога"
                        class="h-40 w-40 rounded-full object-cover shadow"
                    />
                </div>

                <!-- RIGHT COLUMN -->
                <div class="md:col-span-9 space-y-6">

                    <!-- Header -->
                    <div>
                        <h2 class="text-2xl font-semibold text-gray-900">
                            ${ps.full_name}
                        </h2>
                        <p class="mt-1 text-gray-600">
                            ${ps.work_experience
                                ? `Опыт ${ps.work_experience} ${word}`
                                : "Опыт не указан"}
                        </p>

                    </div>

                    <!-- Price -->
                    <div class="rounded-xl bg-gray-50 p-4">
                        <p class="text-sm text-gray-500">
                            Индивидуальная сессия · 50 минут
                        </p>
                        <p class="mt-1 text-xl font-semibold text-gray-900">
                            ${ps.price.value} ${ps.price.currency}
                        </p>
                    </div>

                    <!-- Nearest slot (stub) -->
                    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-xl border p-4">
                        <div>
                            <p class="text-sm text-gray-500">Ближайшая запись</p>
                            <p class="text-gray-900 font-medium">
                                скоро будет доступно
                            </p>
                            <p class="text-xs text-gray-400 mt-1">
                                Часовой пояс: ${ps.timezone || "не указан"}
                            </p>
                        </div>

                        <button
                            type="button"
                            class="rounded-xl bg-indigo-600 px-6 py-2.5 text-white font-medium
                                   hover:bg-indigo-700 transition"
                            onclick="document.getElementById('psychologist-schedule')?.scrollIntoView({behavior: 'smooth'})"
                        >
                            Выбрать время
                        </button>
                    </div>

                    <!-- Biography -->
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900">
                            О специалисте
                        </h3>
                        <p class="mt-2 text-gray-700 leading-relaxed">
                            ${ps.biography || "Описание специалиста не указано"}
                        </p>
                    </div>

                    <!-- Education -->
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900">
                            Образование
                        </h3>
                        ${renderEducations(ps.educations)}
                    </div>

                    <!-- Methods -->
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900">
                            Методы терапии
                        </h3>
                        ${renderBadges(ps.methods, "indigo")}
                    </div>

                    <!-- Topics -->
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900">
                            Работает с темами вашей анкеты
                        </h3>
                        ${renderBadges(ps.matched_topics, "green")}
                    </div>

                    <!-- Schedule -->
                    <div
                        id="psychologist-schedule"
                        class="rounded-xl border border-dashed p-4"
                    >
                        <p class="text-sm text-gray-500">
                            Расписание появится после подключения календаря
                        </p>
                    </div>

                </div>
            </div>
        </div>
    `;

}
