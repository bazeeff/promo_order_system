from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .category import Category
from ...helpers.models import UUIDModel, CreatedModel


class Good(UUIDModel, CreatedModel):
    name = models.CharField(
        "Название",
        max_length=255,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="goods",
        verbose_name="Категория"
    )
    price = models.DecimalField(
        "Цена",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    is_promo_excluded = models.BooleanField(
        "Исключён из промоакций",
        default=False,
    )

    class Meta:
        ordering = ("id",)
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self) -> str:
        return self.name
