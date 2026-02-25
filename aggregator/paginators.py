from rest_framework.pagination import PageNumberPagination


class PsychologistCatalogPagination(PageNumberPagination):
    """Класс-пагинатор для API-контракта *Публичного каталога психологов*.
    Примечание:
        - Этот пагинатор используется именно в DRF-эндпоинте каталога."""

    page_size = 24  # Количество элементов на странице
    page_size_query_param = "page_size"  # Параметр запроса для явного указания размера страницы
    max_page_size = 100  # Защита от слишком тяжелых запросов


class CatalogPagePagination(PageNumberPagination):
    """Класс-пагинатор для WEB-каталога (*Каталог психологов*).
    Примечание:
        - В web-слое каталога сейчас используется встроенный django.core.paginator.Paginator,
          но этот класс оставляем как явный reference на согласованный размер страницы."""

    page_size = 18
    page_size_query_param = "page_size"
    max_page_size = 99
