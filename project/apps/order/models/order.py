from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from .promo_code import PromoCode
from ...helpers.models import UUIDModel, CreatedModel


class Order(UUIDModel, CreatedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Пользователь",
    )
    promo = models.ForeignKey(
        PromoCode,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Промокод",
    )
    idempotency_key = models.CharField(
        "Ключ идемпотентности",
        max_length=128,
        null=True,
        blank=True,
    )
    request_fingerprint = models.CharField(
        "Отпечаток запроса",
        max_length=64,
        null=True,
        blank=True,
    )
    subtotal = models.DecimalField(
        "Сумма до скидки",
        max_digits=14,
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
    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "idempotency_key"),
                condition=Q(idempotency_key__isnull=False),
                name="uniq_order_user_idempotency_key",
            ),
        ]
        ordering = ("-id",)
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
