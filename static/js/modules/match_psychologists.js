import { CLIENT_PROFILE_UPDATED } from "../events/client_profile_events.js";
import { pluralizeRu } from "../utils/pluralize_ru.js";

export function initMatchPsychologists() {

    /**
     * ===== 1) Функция для управления состоянием кнопки "ДАЛЕЕ" =====
     * ===== Кнопка активна, только если найдено больше 0 специалистов =====
     */
    function toggleSubmitButton(count) {
        const btn = document.getElementById("btn-submit-filters");
        if (!btn) return;

        btn.disabled = (count === 0);

        // Также управляем ссылкой перехода на шаг "Выбор психолога" - если 0 специалистов то тоже нельзя дальше идти
        const stepLink = document.getElementById("step-choice-psychologist-link");
        if (stepLink) {
            const isDisabled = (count === 0);
            stepLink.setAttribute("aria-disabled", String(isDisabled));
            stepLink.classList.toggle("pointer-events-none", isDisabled);
        }
    }

    /**
     * ===== 2) Функция для автоматического запуска процесса ФИЛЬТРАЦИИ СПЕЦИАЛИСТА и генерации набора АВАТАР =====
     */
    function updatePsychologistAvatars() {
        fetch("/aggregator/api/match-psychologists/")
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById("avatar-group");
                if (!container) return;

                container.innerHTML = "";

                const items = data.items || [];

                // placeholder "N специалистов"
                const count = items.length;

                // СРАЗУ ОБНОВЛЯЕМ СОСТОЯНИЕ КНОПКИ
                toggleSubmitButton(count);

                const topFive = items.slice(0, 5);

                if (count > 0) {

                    const word = pluralizeRu(
                        count,
                        "психолог",
                        "психолога",
                        "психологов"
                    );

                    const wrap = document.createElement("div");
                    wrap.className = "avatar avatar-placeholder";

                    wrap.innerHTML = `
                        <div class="relative font-medium tracking-wide text-gray-500 bg-white inline-flex w-auto
                            rounded-full border-2 border-white items-center justify-center max-w-xs p-2">
                            <span><strong>${count}</strong> ${word} могут вам подойти</span>
                        </div>
                    `;
                    container.appendChild(wrap);

                } else {

                    // Если не найдено ни одного подходящего специалиста (count === 0)
                    const wrap = document.createElement("div");
                    wrap.className = "avatar avatar-placeholder";

                    wrap.innerHTML = `
                        <div class="relative text-pink-500 bg-white font-bold tracking-wide
                            rounded-full border-2 border-white p-0 text-center max-w-xl">
                            <span>
                                К сожалению, по заданным параметрам нет подходящих психологов.
                                Измените параметры подбора
                            </span>
                        </div>
                    `;
                    container.appendChild(wrap);

                }

                // Показать топ-5 специалистов
                topFive.forEach(ps => {
                    const img = document.createElement("img");
                    img.src = ps.photo || "/static/images/menu/user-circle.svg";
                    img.alt = "avatar";
                    img.className =
                        "relative inline-block h-12 w-12 rounded-full border-2 border-white object-cover object-center";

                    container.appendChild(img);
                });
            })
            .catch(err => {
                console.error("Ошибка загрузки психологов:", err);
                // В случае ошибки API на всякий случай блокируем кнопку, чтобы избежать перехода в пустоту
                toggleSubmitButton(0);
            });
    }

    // запуск при загрузке
    updatePsychologistAvatars();

    // при любом autosave (событие из других модулей)
    document.addEventListener(CLIENT_PROFILE_UPDATED, updatePsychologistAvatars);
}
