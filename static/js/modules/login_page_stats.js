import { pluralizeRu } from "../utils/pluralize_ru.js";

//-------------------------------------------------------------
// Формирование ТЕКСТА со счетчиком АКТИВНЫХ специалистов для страницы login_page.html
//-------------------------------------------------------------

const statsEl = document.getElementById("verified-psychologists-text");
if (statsEl) {
  const count = Number(statsEl.dataset.count || 0);
  const word = pluralizeRu(count, "специалист", "специалиста", "специалистов");
  statsEl.innerHTML = `В команде <span class="font-bold">${count}</span> ${word}, готовых помочь прямо сейчас!`;
}
