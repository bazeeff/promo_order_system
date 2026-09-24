from django.utils.translation import gettext_lazy as _
from rest_framework.pagination import PageNumberPagination


class PerPageNumberPagination(PageNumberPagination):
    page_query_param = "page"
    page_query_description = _("Страница")
    page_size_query_param = "per_page"
    page_size_query_description = _("Элементов на странице")
    max_page_size = 50
