import logging
from decimal import ROUND_HALF_UP, Decimal

from apps.helpers.exceptions import (
    IdempotencyConflict,
    PromoAlreadyUsed,
    PromoExpired,
    PromoInactive,
    PromoNotFound,
    PromoNotApplicable,
    PromoUsageLimitReached,
)
from apps.helpers.services import AbstractService
from apps.order.models import Good, Order, OrderItem, PromoCode, PromoRedemption
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)

_CENT = Decimal("0.01")
_ZERO = Decimal("0")


class OrderCreationService(AbstractService):
    """Создание заказа с применением промокода.

    Вся запись выполняется в одной транзакции. Строка промокода
    блокируется ``select_for_update``, поэтому параллельные заказы
    с одним промокодом сериализуются: проверки лимита использований и
    «один раз на пользователя» видят закоммиченное состояние, а
    ограничения уникальности в БД страхуют от оставшихся гонок.

    Поддерживается идемпотентность: повторный запрос с тем же заголовком
    ``Idempotency-Key`` и тем же телом возвращает уже созданный заказ.
    """

    def process(
        self,
        *,
        user,
        items,
        promocode=None,
        idempotency_key=None,
        request_fingerprint=None,
    ):
        """Создать заказ и применить правила промокода.

        Args:
            user: пользователь, размещающий заказ (из контекста запроса).
            items: список ``{"good": Good, "quantity": int}``.
            promocode: сырой код, как ввёл пользователь; ``None`` — без промокода.
            idempotency_key: значение заголовка Idempotency-Key, если передан.
            request_fingerprint: отпечаток тела запроса для проверки
                идемпотентности.

        Returns:
            Кортеж ``(order, replayed)``: созданный или переигранный заказ и
            признак того, что заказ уже существовал.

        """
        with transaction.atomic():
            if idempotency_key:
                replayed = self._find_replay(user, idempotency_key)
                if replayed is not None:
                    self._check_fingerprint(replayed, request_fingerprint)
                    return replayed, True

            promo = (
                self._lock_and_validate(user, promocode) if promocode else None
            )
            positions = self._build_positions(items)
            if promo is not None:
                positions = self._apply_discount(positions, promo)

            subtotal = sum(
                (position["amount"] for position in positions), _ZERO
            )
            discount_amount = sum(
                (position["discount_amount"] for position in positions), _ZERO
            )

            try:
                with transaction.atomic():
                    order = self._create_order(
                        user=user,
                        promo=promo,
                        positions=positions,
                        subtotal=subtotal,
                        discount_amount=discount_amount,
                        idempotency_key=idempotency_key,
                        request_fingerprint=request_fingerprint,
                    )
            except IntegrityError as exc:
                replayed = self._resolve_race(
                    exc, user, idempotency_key, request_fingerprint
                )
                if replayed is None:
                    raise
                return replayed, True

        logger.info(
            "Order %s created for user %s: subtotal=%s discount=%s total=%s promo=%s",
            order.pk,
            user.pk,
            subtotal,
            discount_amount,
            order.total,
            promo.code if promo else None,
        )
        return order, False

    def _find_replay(self, user, idempotency_key):
        return Order.objects.filter(
            user=user,
            idempotency_key=idempotency_key,
        ).first()

    def _check_fingerprint(self, order, request_fingerprint):
        if order.request_fingerprint != request_fingerprint:
            raise IdempotencyConflict()

    def _lock_and_validate(self, user, raw_code):
        """Заблокировать строку промокода и проверить все правила,
        не зависящие от состава заказа."""
        code = raw_code.strip().upper()
        promo = PromoCode.objects.select_for_update().filter(code=code).first()
        if promo is None:
            raise PromoNotFound()
        if not promo.is_active:
            raise PromoInactive()
        if promo.expires_at <= timezone.now():
            raise PromoExpired()
        if promo.used_count >= promo.max_uses:
            raise PromoUsageLimitReached()
        if promo.redemptions.filter(user=user).exists():
            raise PromoAlreadyUsed()
        return promo

    def _build_positions(self, items):
        """Посчитать базовые суммы позиций со снимком цены каталога."""
        return [
            {
                "good": item["good"],
                "quantity": item["quantity"],
                "unit_price": item["good"].price,
                "amount": self._quantize(
                    item["good"].price * item["quantity"]
                ),
                "discount_rate": _ZERO,
                "discount_amount": _ZERO,
                "total": self._quantize(
                    item["good"].price * item["quantity"]
                ),
            }
            for item in items
        ]

    def _apply_discount(self, positions, promo):
        """Распределить скидку по позициям.

        Скидка не применяется к товарам вне акций (``is_promo_excluded``) и,
        если промокод ограничен категорией, к товарам других категорий.
        Если подходящих позиций нет — заказ не создаётся.
        """
        if not any(
            self._is_eligible(promo, position["good"]) for position in positions
        ):
            raise PromoNotApplicable()

        discounted = []
        for position in positions:
            item_discount = _ZERO
            item_rate = _ZERO
            if self._is_eligible(promo, position["good"]):
                item_rate = promo.discount_rate
                item_discount = self._quantize(
                    position["amount"] * promo.discount_rate
                )
            discounted.append(
                {
                    **position,
                    "discount_rate": item_rate,
                    "discount_amount": item_discount,
                    "total": position["amount"] - item_discount,
                }
            )
        return discounted

    @staticmethod
    def _is_eligible(promo, good: Good) -> bool:
        if good.is_promo_excluded:
            return False
        return promo.category_id is None or promo.category_id == good.category_id

    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        return value.quantize(_CENT, rounding=ROUND_HALF_UP)

    def _create_order(
        self,
        *,
        user,
        promo,
        positions,
        subtotal,
        discount_amount,
        idempotency_key,
        request_fingerprint,
    ) -> Order:
        order = Order.objects.create(
            user=user,
            promo=promo,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint if idempotency_key else None,
            subtotal=subtotal,
            discount_rate=promo.discount_rate if promo else _ZERO,
            discount_amount=discount_amount,
            total=subtotal - discount_amount,
        )
        OrderItem.objects.bulk_create(
            OrderItem(
                order=order,
                good=position["good"],
                quantity=position["quantity"],
                unit_price=position["unit_price"],
                discount_rate=position["discount_rate"],
                discount_amount=position["discount_amount"],
                total=position["total"],
            )
            for position in positions
        )
        if promo is not None:
            PromoRedemption.objects.create(user=user, promo=promo, order=order)
            PromoCode.objects.filter(pk=promo.pk).update(
                used_count=F("used_count") + 1
            )
        return order

    def _resolve_race(self, exc, user, idempotency_key, request_fingerprint):
        """Разобрать конфликт уникальности, возникший из-за гонки.

        Возвращает переигранный заказ для повторного Idempotency-Key,
        выбрасывает доменную ошибку для гонки по промокоду и ``None``,
        если ошибку следует пробросить как есть.
        """
        text = str(exc).lower()
        if self._is_idempotency_race(text):
            replayed = self._find_replay(user, idempotency_key)
            if replayed is not None:
                self._check_fingerprint(replayed, request_fingerprint)
                return replayed
        if self._is_promo_race(text):
            raise PromoAlreadyUsed() from exc
        return None

    @staticmethod
    def _is_idempotency_race(text: str) -> bool:
        return "uniq_order_user_idempotency_key" in text or (
            "idempotency_key" in text
        )

    @staticmethod
    def _is_promo_race(text: str) -> bool:
        return "uniq_promo_per_user" in text or "promoredemption" in text
