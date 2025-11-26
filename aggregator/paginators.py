from rest_framework.pagination import PageNumberPagination


class PsychologistCatalogPagination(PageNumberPagination):
    """Класс-пагинатор для страницы с *Публичным каталогом психологов*."""

    page_size = 24  # Количество элементов на странице
    page_size_query_param = "page_size"  # Название параметра запроса для указания кол-ва элементов на странице
    max_page_size = 100  # Максимальное количество элементов на странице
