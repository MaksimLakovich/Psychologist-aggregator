/**
 * Бизнес-смысл модуля:
 * Карточка имеет липкую левую колонку с фото. Чтобы фото и компаньон не
 * "подлипали" под верхнюю дорожную карту шагов, считаем ее реальную высоту
 * и задаем CSS-переменную корректного отступа.
 */

export function applyChoiceHeaderOffset({
    headerId = "choice-sticky-header",
    cssVarName = "--choice-header-offset",
    buffer = 64, // 4rem визуального воздуха (1rem = 16 / 64 = 4rem)
} = {}) {
    const header = document.getElementById(headerId);
    if (!header) return;

    const rect = header.getBoundingClientRect();
    document.documentElement.style.setProperty(cssVarName, `${rect.height + buffer}px`);
}
