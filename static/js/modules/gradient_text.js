const DEFAULT_GRADIENT_OPTIONS = {
  colors: ["#5227FF", "#FF9FFC", "#B19EEF"],
  animationSpeed: 8,
  direction: "horizontal",
  pauseOnHover: false,
  yoyo: true,
};

function parseDirection(direction) {
  if (direction === "vertical") {
    return {
      gradientAngle: "to bottom",
      backgroundSize: "100% 300%",
      position: (p) => `50% ${p}%`,
    };
  }

  if (direction === "diagonal") {
    return {
      gradientAngle: "to bottom right",
      backgroundSize: "300% 300%",
      position: (p) => `${p}% 50%`,
    };
  }

  return {
    gradientAngle: "to right",
    backgroundSize: "300% 100%",
    position: (p) => `${p}% 50%`,
  };
}

function applyGradientText(el, options) {
  const { colors, animationSpeed, direction, pauseOnHover, yoyo } = {
    ...DEFAULT_GRADIENT_OPTIONS,
    ...options,
  };

  if (!el || !Array.isArray(colors) || colors.length < 2) return;

  const { gradientAngle, backgroundSize, position } = parseDirection(direction);
  const gradientColors = [...colors, colors[0]].join(", ");
  const duration = Math.max(0.1, Number(animationSpeed)) * 1000;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  el.style.backgroundImage = `linear-gradient(${gradientAngle}, ${gradientColors})`;
  el.style.backgroundSize = backgroundSize;
  el.style.backgroundRepeat = "repeat";
  el.style.backgroundClip = "text";
  el.style.webkitBackgroundClip = "text";
  el.style.color = "transparent";
  el.style.webkitTextFillColor = "transparent";
  el.style.willChange = "background-position";

  if (reduceMotion) {
    el.style.backgroundPosition = position(50);
    return;
  }

  let paused = false;
  let elapsed = 0;
  let lastTime = null;

  const step = (time) => {
    if (paused) {
      lastTime = null;
      requestAnimationFrame(step);
      return;
    }

    if (lastTime === null) {
      lastTime = time;
      requestAnimationFrame(step);
      return;
    }

    elapsed += time - lastTime;
    lastTime = time;

    let p;
    if (yoyo) {
      const fullCycle = duration * 2;
      const cycleTime = elapsed % fullCycle;
      p = cycleTime < duration ? (cycleTime / duration) * 100 : 100 - ((cycleTime - duration) / duration) * 100;
    } else {
      p = (elapsed / duration) * 100;
    }

    el.style.backgroundPosition = position(p);
    requestAnimationFrame(step);
  };

  if (pauseOnHover) {
    el.addEventListener("mouseenter", () => {
      paused = true;
    });
    el.addEventListener("mouseleave", () => {
      paused = false;
    });
  }

  requestAnimationFrame(step);
}

function parseJSONAttribute(rawValue, fallback) {
  if (!rawValue) return fallback;
  try {
    return JSON.parse(rawValue);
  } catch {
    return fallback;
  }
}

const title = document.getElementById("login-gradient-title");
if (title) {
  applyGradientText(title, {
    colors: parseJSONAttribute(title.dataset.gradientColors, DEFAULT_GRADIENT_OPTIONS.colors),
    animationSpeed: Number(title.dataset.gradientSpeed || DEFAULT_GRADIENT_OPTIONS.animationSpeed),
    direction: title.dataset.gradientDirection || DEFAULT_GRADIENT_OPTIONS.direction,
    pauseOnHover: title.dataset.gradientPauseOnHover === "true",
    yoyo:
      title.dataset.gradientYoyo !== undefined
        ? title.dataset.gradientYoyo !== "false"
        : DEFAULT_GRADIENT_OPTIONS.yoyo,
  });
}
