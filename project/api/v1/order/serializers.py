import re

from apps.helpers.serializers import EagerLoadingSerializerMixin
from apps.order.models import Category, Good, Order, OrderItem, PromoCode
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

PROMO_CODE_PATTERN = re.compile(r"^[0-9A-Za-z_-]{1,64}$")


class CategorySerializer(serializers.ModelSerializer):
    """Чтение категории."""

    class Meta:
        model = Category
        fields = ("id", "name", "created_at")


class CategoryWriteSerializer(serializers.ModelSerializer):
    """Создание/изменение категории."""

    class Meta:
        model = Category
        fields = ("id", "name")


class GoodSerializer(
    EagerLoadingSerializerMixin, serializers.ModelSerializer
):
    """Чтение товара."""

    category_name = serializers.StringRelatedField(source="category")
    select_related_fields = ("category",)

    class Meta:
        model = Good
        fields = (
            "id",
            "name",
            "category",
            "category_name",
            "price",
            "is_promo_excluded",
            "created_at",
        )


class GoodWriteSerializer(serializers.ModelSerializer):
    """Создание/изменение товара."""

    class Meta:
        model = Good
        fields = ("id", "name", "category", "price", "is_promo_excluded")


class PromoCodeSerializer(
    EagerLoadingSerializerMixin, serializers.ModelSerializer
):
    """Чтение промокода."""

    category_name = serializers.StringRelatedField(source="category")
    select_related_fields = ("category",)

    class Meta:
        model = PromoCode
        fields = (
            "id",
            "code",
            "discount_rate",
            "expires_at",
            "max_uses",
            "used_count",
            "category",
            "category_name",
            "is_active",
            "created_at",
        )


class PromoCodeWriteSerializer(serializers.ModelSerializer):
    """Создание/изменение промокода.

    ``used_count`` увеличивается только сервисом создания заказа,
    поэтому из API он недоступен.
    """

    class Meta:
        model = PromoCode
        fields = (
            "id",
            "code",
            "discount_rate",
            "expires_at",
            "max_uses",
            "category",
            "is_active",
        )

    def validate(self, attrs):
        expires_at = attrs.get(
            "expires_at", getattr(self.instance, "expires_at", None)
        )
        if expires_at and expires_at <= timezone.now():
            raise ValidationError(
                {"expires_at": "Дата окончания должна быть в будущем."}
            )
        return attrs


class OrderItemCreateSerializer(serializers.Serializer):
    """Вход одной позиции заказа."""

    good = serializers.PrimaryKeyRelatedField(
        queryset=Good.objects.all(),
    )
    quantity = serializers.IntegerField(min_value=1, max_value=1000)


class OrderCreateSerializer(serializers.Serializer):
    """Вход эндпоинта создания заказа.

    Пользователь берётся из контекста запроса (аутентификация),
    а не из тела. ``promocode`` опционален; пустая строка считается
    отсутствием промокода.
    """

    items = OrderItemCreateSerializer(many=True, allow_empty=False)
    promocode = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=64,
    )

    def validate_promocode(self, value):
        value = value.strip()
        if not value:
            return None
        if not PROMO_CODE_PATTERN.fullmatch(value):
            raise ValidationError(
                "Промокод может содержать буквы, цифры, '-' и '_'."
            )
        return value

    def validate_items(self, items):
        good_ids = [item["good"].pk for item in items]
        if len(good_ids) != len(set(good_ids)):
            raise ValidationError(
                "Каждый товар может встречаться в заказе один раз;"
                " объедините позиции."
            )
        return items


class OrderItemSerializer(serializers.ModelSerializer):
    """Чтение позиции заказа со снимком цены на момент покупки."""

    good = serializers.PrimaryKeyRelatedField(read_only=True)
    good_name = serializers.StringRelatedField(source="good")

    class Meta:
        model = OrderItem
        fields = (
            "good",
            "good_name",
            "quantity",
            "unit_price",
            "discount_rate",
            "discount_amount",
            "total",
        )


class PromoBriefSerializer(serializers.ModelSerializer):
    """Краткое представление промокода внутри ответа заказа."""

    class Meta:
        model = PromoCode
        fields = ("code", "discount_rate")


class OrderSerializer(
    EagerLoadingSerializerMixin, serializers.ModelSerializer
):
    """Чтение заказа: позиции, снимки цен и применённая скидка."""

    user = serializers.PrimaryKeyRelatedField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    promo = PromoBriefSerializer(read_only=True)
    select_related_fields = ("user", "promo")
    prefetch_related_fields = ("items__good",)

    class Meta:
        model = Order
        fields = (
            "id",
            "user",
            "items",
            "subtotal",
            "discount_rate",
            "discount_amount",
            "total",
            "promo",
            "created_at",
        )
