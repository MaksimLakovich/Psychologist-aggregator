import { CLIENT_PROFILE_UPDATED } from "../events/client_profile_events.js";

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

                // первые 5
                topFive.forEach(ps => {
                    const img = document.createElement("img");
                    img.src = ps.photo || "/static/images/menu/user-circle.svg";
                    img.alt = "avatar";
                    img.className =
                        "relative inline-block h-12 w-12 rounded-full border-2 border-white object-cover object-center";

                    container.appendChild(img);
                });

                // placeholder "+N специалистов"
                const remaining = items.length - topFive.length;
                if (remaining > 0) {
                    const wrap = document.createElement("div");
                    wrap.className = "avatar avatar-placeholder";

                    wrap.innerHTML = `
                        <div class="relative bg-white inline-flex w-auto rounded-full border-2 border-white
                            items-center justify-center max-w-xs p-2">
                            <span>+${remaining} специалистов могут вам подойти</span>
                        </div>
                    `;
                    container.appendChild(wrap);
                }
            })
            .catch(err => console.error("Ошибка загрузки психологов:", err));
    }

    // запуск при загрузке
    updatePsychologistAvatars();

    // при любом autosave
    document.addEventListener(CLIENT_PROFILE_UPDATED, updatePsychologistAvatars);

}
