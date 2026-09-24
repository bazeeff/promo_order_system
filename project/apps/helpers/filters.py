from django_filters import Filter
from django_filters.constants import EMPTY_VALUES


class ListFilter(Filter):
    """
    ListFilter позволяет производить фильтрацию по спискам значений, разделённых запятыми.

    Примерное использование:
        <поле> = ListFilter(field_name='<название в модели>', queryset=<модель>.objects.all(), lookup_expr='in')

    """

    def filter(self, queryset, value):  # noqa: WPS110
        if value in EMPTY_VALUES:
            return queryset
        return super().filter(
            queryset, [item.strip() for item in value.split(",")]
        )  # noqa: WPS221 WPS110
