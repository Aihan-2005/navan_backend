from rest_framework.pagination import PageNumberPagination


class ListeningContentPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "pageSize"
    max_page_size = 50
