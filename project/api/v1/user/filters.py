from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet  # noqa: WPS347
from django_filters import CharFilter, FilterSet

User = get_user_model()


class UserFilterSet(FilterSet):
    search_login = CharFilter(method="filter_search_login")

    class Meta:
        model = User
        fields = ("first_name", "email")

    def filter_search_login(
        self, queryset: QuerySet, name: str, value: str
    ) -> QuerySet:  # noqa: WPS110
        return queryset.filter(Q(first_name=value) or Q(email=value))
