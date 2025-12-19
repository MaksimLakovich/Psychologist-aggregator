import { initPsychologistsChoice } from "../modules/match_ps_choice.js";

document.addEventListener("DOMContentLoaded", () => {


    // 1. Получаем карточки отфильтрованных психологов по указанным клиентом параметрам
    initPsychologistsChoice();


    // 2. Вычисляем высоту header для блока "<!-- LEFT COLUMN -->" в match_ps_choice.js чтоб фото психолога не скроллилось вниз
    const header = document.getElementById("choice-sticky-header");

    if (header) {
        const rect = header.getBoundingClientRect();
        const buffer = 64; // 4rem визуального воздуха (1rem = 16 / 64 = 4rem)

        document.documentElement.style.setProperty(
            "--choice-header-offset",
            `${rect.height + buffer}px`
        );
    }

});
