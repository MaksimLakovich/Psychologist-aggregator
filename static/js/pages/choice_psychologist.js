import { initPsychologistsChoice } from "../modules/match_ps_choice.js";
import { applyChoiceHeaderOffset } from "../modules/detail_card/detail_card_header_offset.js";

document.addEventListener("DOMContentLoaded", () => {
    // 1. Загружаем подбор психологов по указанным клиентом параметрам и отрисовываем карточку выбранного специалиста.
    initPsychologistsChoice();

    // 2. Вычисляем отступ липкой колонки относительно верхней дорожной карты шагов, чтоб фото психолога не скроллилось вниз
    applyChoiceHeaderOffset();
});
