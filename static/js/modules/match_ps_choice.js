import { initStickyHeaderBehavior } from "./detail_card/detail_card_sticky_companion.js";
import { initDetailCardModals } from "./detail_card/detail_card_modals.js";
import { initGlobalTextToggleHandlers } from "./detail_card/detail_card_content_toggle.js";
import { renderPsychologistCard } from "./detail_card/detail_card_render.js";
import { initSessionChoiceState } from "./detail_card/detail_card_session_choice.js";

/**
 * Бизнес-смысл модуля:
 * Это основной сценарий страницы "Выбор психолога" после анкеты.
 * Здесь клиент листает предложенных специалистов, открывает карточку
 * и выбирает удобный слот для перехода к записи и оплате.
 */


// Глобальное состояние страницы (список психологов + пагинация + выбранный психолог)
let psychologists = [];
let currentOffset = 0;
const PAGE_SIZE = 10;
let selectedPsychologistId = null;

// Восстанавливаем "страницу" аватаров по выбранному психологу.
// Бизнес-смысл: если клиент уже выбрал специалиста на 2/3/... наборе,
// после обновления страницы или возврата назад он должен видеть тот же набор,
// а не первый экран аватаров.
function syncOffsetToSelectedPsychologist() {
    if (!psychologists.length || !selectedPsychologistId) {
        currentOffset = 0;
        return;
    }

    const selectedIndex = psychologists.findIndex(
        ps => String(ps.id) === String(selectedPsychologistId)
    );

    if (selectedIndex < 0) {
        currentOffset = 0;
        return;
    }

    currentOffset = Math.floor(selectedIndex / PAGE_SIZE) * PAGE_SIZE;
}

// Плавно скроллим вверх и дожидаемся фактической остановки,
// чтобы перерисовка карточки не происходила в середине движения экрана.
function scrollToTopThen(callback) {
    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });

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

        if (sameCount >= 3) {
            if (typeof callback === "function") {
                callback();
            }
            return;
        }

        requestAnimationFrame(check);
    };

    requestAnimationFrame(check);
}

function getPsychologistsList() {
    return psychologists;
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
            // В сценарии неудачного resume-booking сервер возвращает specialist_profile_id в query string.
            // Это нужно, чтобы повторно открыть именно ранее выбранного специалиста,
            // а не заставлять клиента заново искать его по всем наборам аватаров.
            const preferredPsychologistId = new URLSearchParams(window.location.search).get("specialist_profile_id");

            if (shouldReset) {
                sessionStorage.removeItem("selectedPsychologistId");
                cardContainer.dataset.resetChoice = "0";
            }

            let selected = null;

            // 1) Сценарий 1: если URL уже содержит specialist_profile_id, приоритетно открываем именно его.
            if (preferredPsychologistId) {
                selected = psychologists.find(
                    ps => String(ps.id) === String(preferredPsychologistId)
                ) || null;
            }

            // 2) Сценарий 2: если специального id нет, пытаемся восстановить последнего выбранного психолога.
            if (!selected) {
                const selectedId = sessionStorage.getItem("selectedPsychologistId");
                selected = psychologists.find(ps => String(ps.id) === selectedId) || null;
            }

            // 3) Сценарий 3: если ни один из вариантов не подошел, берем первого специалиста из текущей выдачи.
            if (!selected) {
                selected = psychologists[0];
            }

            selectedPsychologistId = selected.id;
            // Синхронизируем выбранного психолога с sessionStorage (важно при новом подборе)
            sessionStorage.setItem("selectedPsychologistId", selectedPsychologistId);
            syncOffsetToSelectedPsychologist();

            renderAvatars();

            scrollToTopThen(() => {
                renderPsychologistCard(selected);
                initStickyHeaderBehavior();
            });
        })
        .catch(error => {
            console.error("Ошибка загрузки психологов:", error);
        });
}


// ===== ШАГ 2: РЕНДЕР АВАТАРОВ =====
function renderAvatars() {
    const container = document.getElementById("avatar-group");
    if (!container) return;

    const baseAvatarClass = container.dataset.avatarClass || "";
    container.innerHTML = "";

    const pageItems = psychologists.slice(currentOffset, currentOffset + PAGE_SIZE);

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
            sessionStorage.setItem("selectedPsychologistId", selectedPsychologistId);

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

export function initPsychologistsChoice() {
    initGlobalTextToggleHandlers();
    initDetailCardModals({ getPsychologistsList });
    initSessionChoiceState();

    fetchPsychologists();
    initNavigation();
}
