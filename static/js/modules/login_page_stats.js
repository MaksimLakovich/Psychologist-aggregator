import { pluralizeRu } from "../utils/pluralize_ru.js";

const statsEl = document.getElementById("verified-psychologists-text");
if (statsEl) {
  const count = Number(statsEl.dataset.count || 0);
  const word = pluralizeRu(count, "специалист", "специалиста", "специалистов");
  statsEl.innerHTML = `В команде <span class="font-bold">${count}</span> ${word}, готовых помочь в любое время суток`;
}
