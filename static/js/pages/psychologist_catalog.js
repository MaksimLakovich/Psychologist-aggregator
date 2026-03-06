import { bootstrapCatalogPage } from "../modules/catalog/catalog_page.js";

/**
 * Тонкий entry-point страницы каталога.
 *
 * Вся page-level логика теперь разнесена по `static/js/modules/catalog_*.js`,
 * а здесь остается только запуск bootstrap после готовности DOM.
 */

document.addEventListener("DOMContentLoaded", () => {
    bootstrapCatalogPage().catch((error) => {
        console.error("Ошибка инициализации каталога:", error);
    });
});
