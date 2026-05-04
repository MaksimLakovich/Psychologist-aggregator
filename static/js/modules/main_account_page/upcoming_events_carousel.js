/**
 * Карусель ближайших встреч на главной странице кабинета специалиста.
 *
 * Бизнес-смысл:
 * - специалист по умолчанию видит самую ближайшую встречу как главное рабочее событие;
 * - соседние встречи показываются по бокам, чтобы было понятно, что в расписании есть продолжение;
 * - на первом событии нельзя листать назад, а на последнем нельзя листать вперед, потому что порядок встреч
 *   должен оставаться календарным, без зацикливания;
 * - клик по боковой карточке, стрелкам или индикатору быстро переводит специалиста к нужной встрече.
 */

// Единый список CSS-состояний карточки встречи. Перед каждой сменой активной встречи
// очищаем старое состояние и назначаем новое: текущая, предыдущая, следующая или скрытая в глубине карусели
const carouselClassNames = [
    "is-active",
    "is-prev",
    "is-next",
    "hidden-prev",
    "hidden-next",
];

const clampIndex = (index, maxIndex) => Math.min(Math.max(index, 0), maxIndex);

// Индекс активной встречи приходит из data-атрибута шаблона.
// Если в разметке окажется некорректное значение, спокойно возвращаемся к ближайшей встрече
const parseIndex = (value, fallback = 0) => {
    const parsedValue = Number.parseInt(value, 10);
    return Number.isNaN(parsedValue) ? fallback : parsedValue;
};

// Стрелки должны честно показывать границы расписания:
// на первой встрече не даем листать назад, на последней - вперед
const setControlState = (button, isDisabled) => {
    if (!button) {
        return;
    }

    button.disabled = isDisabled;
    button.setAttribute("aria-disabled", String(isDisabled));
    button.classList.toggle("opacity-40", isDisabled);
    button.classList.toggle("cursor-not-allowed", isDisabled);
    button.classList.toggle("hover:bg-indigo-50", !isDisabled);
    button.classList.toggle("hover:text-indigo-600", !isDisabled);
    button.classList.toggle("hover:border-indigo-200", !isDisabled);
    button.classList.toggle("hover:shadow-md", !isDisabled);
};

document.querySelectorAll("[data-upcoming-carousel]").forEach((carousel) => {
    // Одна карусель = один независимый список ближайших встреч.
    // Все элементы берем через data-атрибуты, чтобы логика не зависела от декоративных CSS-классов
    const carouselShell = carousel.closest("[data-upcoming-carousel-shell]") || carousel;
    const slides = Array.from(carousel.querySelectorAll("[data-upcoming-slide]"));
    const indicators = Array.from(carousel.querySelectorAll("[data-upcoming-indicator]"));
    const prevButton = carouselShell.querySelector("[data-upcoming-prev]");
    const nextButton = carouselShell.querySelector("[data-upcoming-next]");
    const lastIndex = slides.length - 1;

    if (slides.length === 0) {
        return;
    }

    let activeIndex = clampIndex(parseIndex(carousel.dataset.activeIndex), lastIndex);

    // Главная функция карусели: выбирает встречу, которую специалист сейчас смотрит,
    // и раскладывает остальные карточки вокруг нее как предыдущую/следующую или скрытые
    const setActiveIndex = (nextIndex) => {
        activeIndex = clampIndex(nextIndex, lastIndex);
        carousel.dataset.activeIndex = String(activeIndex);

        slides.forEach((slide, index) => {
            slide.classList.remove(...carouselClassNames);

            // position показывает место карточки относительно текущей встречи:
            // -1 = предыдущая слева, 0 = активная по центру, 1 = следующая справа
            const position = index - activeIndex;
            const isActive = position === 0;

            if (isActive) {
                slide.classList.add("is-active");
            } else if (position === -1) {
                slide.classList.add("is-prev");
            } else if (position === 1) {
                slide.classList.add("is-next");
            } else if (position < -1) {
                slide.classList.add("hidden-prev");
            } else {
                slide.classList.add("hidden-next");
            }

            slide.setAttribute("aria-hidden", String(!isActive));
        });

        // Индикаторы дублируют позицию в расписании на компактных экранах.
        // Активная точка расширяется, чтобы специалист видел, какую встречу он сейчас открыл
        indicators.forEach((indicator, index) => {
            const isActive = index === activeIndex;
            indicator.classList.toggle("bg-indigo-600", isActive);
            indicator.classList.toggle("w-6", isActive);
            indicator.classList.toggle("bg-slate-300", !isActive);
            indicator.classList.toggle("w-2", !isActive);
            indicator.setAttribute("aria-current", isActive ? "true" : "false");
        });

        setControlState(prevButton, activeIndex === 0);
        setControlState(nextButton, activeIndex === lastIndex);
    };

    // Стрелки переводят специалиста строго к соседней встрече по календарному порядку
    prevButton?.addEventListener("click", () => {
        setActiveIndex(activeIndex - 1);
    });

    nextButton?.addEventListener("click", () => {
        setActiveIndex(activeIndex + 1);
    });

    // Боковые карточки выглядят как миниатюры, но остаются быстрым способом перейти
    // к предыдущей или следующей встрече без отдельного поиска в списке
    slides.forEach((slide, index) => {
        slide.addEventListener("click", (event) => {
            if (index === activeIndex) {
                return;
            }

            event.preventDefault();
            setActiveIndex(index);
        });
    });

    // На мобильных и узких экранах индикаторы помогают быстро перейти к нужной встрече,
    // когда боковые карточки занимают слишком много места или менее заметны
    indicators.forEach((indicator) => {
        indicator.addEventListener("click", () => {
            setActiveIndex(parseIndex(indicator.dataset.index, activeIndex));
        });
    });

    // Поддерживаем клавиатуру: специалист может пролистывать встречи стрелками,
    // если фокус находится внутри блока карусели
    carousel.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") {
            event.preventDefault();
            setActiveIndex(activeIndex - 1);
        }

        if (event.key === "ArrowRight") {
            event.preventDefault();
            setActiveIndex(activeIndex + 1);
        }
    });

    // Делаем блок доступным для фокуса и сразу приводим разметку к единому состоянию
    carousel.setAttribute("tabindex", "0");
    setActiveIndex(activeIndex);
});
