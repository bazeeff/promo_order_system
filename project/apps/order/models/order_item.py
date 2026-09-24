from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .good import Good
from .order import Order
from ...helpers.models import CreatedModel, UUIDModel


class OrderItem(UUIDModel, CreatedModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Заказ",
    )
    good = models.ForeignKey(
        Good,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="Товар",
    )
    quantity = models.PositiveIntegerField(
        "Количество",
        validators=[MinValueValidator(1)],
    )
    unit_price = models.DecimalField(
        "Цена за единицу",
        max_digits=12,
        decimal_places=2,
    )
    discount_rate = models.DecimalField(
        "Размер скидки",
        max_digits=5,
        decimal_places=4,
        default=Decimal("0"),
    )
    discount_amount = models.DecimalField(
        "Сумма скидки",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
    )
    total = models.DecimalField(
        "Итоговая сумма",
        max_digits=14,
        decimal_places=2,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("order", "good"),
                name="uniq_good_per_order",
            ),
        ]
        ordering = ("id",)
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
