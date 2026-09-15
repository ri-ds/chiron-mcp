# Pagination classes for Chiron API

from rest_framework.pagination import PageNumberPagination


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination Class for Large Results Sets`
    """

    page_size = 1000
    page_size_query_param = "page_size"
    max_page_size = 10000
