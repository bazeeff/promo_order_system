from apps.order.models import Good, Order, PromoCode
from django_filters import CharFilter, FilterSet


class GoodFilterSet(FilterSet):
    """Фильтр каталога: по категории и участию в акциях."""

    class Meta:
        model = Good
        fields = ("category", "is_promo_excluded")


class PromoCodeFilterSet(FilterSet):
    """Фильтр промокодов: по активности и категории."""

    class Meta:
        model = PromoCode
        fields = ("is_active", "category")


class OrderFilterSet(FilterSet):
    """Фильтр заказов: по пользователю и коду применённого промокода.

    Фильтр по пользователю имеет смысл для администраторов:
    обычные пользователи и так видят только свои заказы.
    """

    promo_code = CharFilter(field_name="promo__code")

    class Meta:
        model = Order
        fields = ("user",)
