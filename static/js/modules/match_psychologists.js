import { CLIENT_PROFILE_UPDATED } from "../events/client_profile_events.js";
import { pluralizeRu } from "../utils/pluralize_ru.js";

export function initMatchPsychologists() {

    function updatePsychologistAvatars() {
        fetch("/aggregator/api/match-psychologists/")
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById("avatar-group");
                if (!container) return;

                container.innerHTML = "";

                const items = data.items || [];
                const topFive = items.slice(0, 5);

                // placeholder "N специалистов"
                // const remaining = items.length - topFive.length;
                const remaining = items.length;

                if (remaining > 0) {

                    const word = pluralizeRu(
                        remaining,
                        "психолог",
                        "психолога",
                        "психологов"
                    );

                    const wrap = document.createElement("div");
                    wrap.className = "avatar avatar-placeholder";

                    wrap.innerHTML = `
                        <div class="relative font-medium text-gray-500 bg-white inline-flex w-auto
                            rounded-full border-2 border-white items-center justify-center max-w-xs p-2">
                            <span><strong>${remaining}</strong> ${word} могут вам подойти</span>
                        </div>
                    `;
                    container.appendChild(wrap);

                } else {

                    // remaining === 0

                    const wrap = document.createElement("div");
                    wrap.className = "avatar avatar-placeholder";

                    wrap.innerHTML = `
                        <div class="relative font-medium text-pink-500 bg-white
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
            .catch(err => console.error("Ошибка загрузки психологов:", err));
    }

    // запуск при загрузке
    updatePsychologistAvatars();

    // при любом autosave
    document.addEventListener(CLIENT_PROFILE_UPDATED, updatePsychologistAvatars);

}
