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

/* ========================
   ЗАГРУЗКА ДАННЫХ
======================== */
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

/* ========================
   РЕНДЕР АВАТАРОВ
======================== */
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

/* ========================
   НАВИГАЦИЯ (кнопки ВЛЕВО / ВПРАВО)
======================== */
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

/* ========================
   КАРТОЧКА ПСИХОЛОГА (пока заглушка)
======================== */
function renderPsychologistCard(ps) {
    const container = document.getElementById("psychologist-card");
    if (!container) return;

    container.innerHTML = `
        <div class="mt-8 rounded-xl border p-6 bg-white shadow">
            <div class="flex gap-6 items-center">
                <img src="${ps.photo}" class="h-32 w-32 rounded-full object-cover" />
                <div>
                    <p class="text-xl font-semibold">${ps.email}</p>
                    <p class="text-gray-600 mt-2">
                        Совпадение тем: ${ps.topic_score}
                    </p>
                    <p class="text-gray-600">
                        Совпадение методов: ${ps.method_score}
                    </p>
                </div>
            </div>
        </div>
    `;

}
