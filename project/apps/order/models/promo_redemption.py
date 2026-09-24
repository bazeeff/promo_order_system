from django.conf import settings
from django.db import models

from .order import Order
from .promo_code import PromoCode
from ...helpers.models import UUIDModel, CreatedModel


class PromoRedemption(UUIDModel, CreatedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="promo_redemptions",
        verbose_name="Пользователь",
    )
    promo = models.ForeignKey(
        PromoCode,
        on_delete=models.PROTECT,
        related_name="redemptions",
        verbose_name="Промокод",
    )
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="promo_redemption",
        verbose_name="Заказ",
    )
    created_at = models.DateTimeField(
        "Дата использования",
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "promo"),
                name="uniq_promo_per_user",
            ),
        ]
        ordering = ("id",)
        verbose_name = "Использование промокода"
        verbose_name_plural = "Использования промокода"
