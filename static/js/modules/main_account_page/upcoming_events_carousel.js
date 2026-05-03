const carouselClassNames = [
    "is-active",
    "is-prev",
    "is-next",
    "hidden-prev",
    "hidden-next",
];

const clampIndex = (index, maxIndex) => Math.min(Math.max(index, 0), maxIndex);

const parseIndex = (value, fallback = 0) => {
    const parsedValue = Number.parseInt(value, 10);
    return Number.isNaN(parsedValue) ? fallback : parsedValue;
};

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

    const setActiveIndex = (nextIndex) => {
        activeIndex = clampIndex(nextIndex, lastIndex);
        carousel.dataset.activeIndex = String(activeIndex);

        slides.forEach((slide, index) => {
            slide.classList.remove(...carouselClassNames);

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

    prevButton?.addEventListener("click", () => {
        setActiveIndex(activeIndex - 1);
    });

    nextButton?.addEventListener("click", () => {
        setActiveIndex(activeIndex + 1);
    });

    slides.forEach((slide, index) => {
        slide.addEventListener("click", (event) => {
            if (index === activeIndex) {
                return;
            }

            event.preventDefault();
            setActiveIndex(index);
        });
    });

    indicators.forEach((indicator) => {
        indicator.addEventListener("click", () => {
            setActiveIndex(parseIndex(indicator.dataset.index, activeIndex));
        });
    });

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

    carousel.setAttribute("tabindex", "0");
    setActiveIndex(activeIndex);
});
