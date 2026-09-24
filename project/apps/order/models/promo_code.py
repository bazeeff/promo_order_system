from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

from .category import Category
from ...helpers.models import CreatedModel, UUIDModel


class PromoCode(UUIDModel, CreatedModel):
    code = models.CharField(
        "Промокод",
        max_length=64,
        unique=True,
    )
    discount_rate = models.DecimalField(
        "Размер скидки",
        max_digits=5,
        decimal_places=4,
        validators=[
            MinValueValidator(Decimal("0.0001")),
            MaxValueValidator(Decimal("1.0000")),
        ],
        help_text="Доля от 0 до 1; например, 0.1 означает скидку 10%.",
    )
    expires_at = models.DateTimeField(
        "Дата окончания действия",
    )
    max_uses = models.PositiveIntegerField(
        "Максимальное количество использований",
        validators=[MinValueValidator(1)],
    )
    used_count = models.PositiveIntegerField(
        "Количество использований",
        default=0,
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="promo_codes",
        help_text="Если указана, промокод применяется только к товарам этой категории.",
        verbose_name="Категория",
    )
    is_active = models.BooleanField(
        "Активен",
        default=True,
    )
    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(used_count__lte=F("max_uses")),
                name="promo_used_lte_max",
            ),
        ]
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.code
