from datetime import timedelta
from decimal import Decimal
from unittest import TestCase

import pytest
from apps.order.models import Category, Good, Order, PromoCode, PromoRedemption
from apps.user.models.user import RoleChoices, User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

ORDER_CREATE_URL = reverse("api_v1:order-create")
ORDERS_LIST_URL = reverse("api_v1:api-root:order-list")


def make_user(email="customer@example.com", role=RoleChoices.PERFORMER_TASK):
    return User.objects.create_user(
        email=email,
        password="test-password-123",
        first_name="Customer",
        role=role,
    )


def make_good(category, **overrides):
    defaults = {
        "name": "Товар",
        "price": Decimal("100.00"),
        "category": category,
    }
    defaults.update(overrides)
    return Good.objects.create(**defaults)


def make_promo(**overrides):
    defaults = {
        "code": "welcome10",
        "discount_rate": Decimal("0.1"),
        "expires_at": timezone.now() + timedelta(days=1),
        "max_uses": 10,
    }
    defaults.update(overrides)
    return PromoCode.objects.create(**defaults)


def order_payload(good, quantity=1, promocode=None):
    payload = {
        "items": [{"good": str(good.pk), "quantity": quantity}],
    }
    if promocode is not None:
        payload["promocode"] = promocode
    return payload


@pytest.mark.django_db
class OrderCreateTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(name="Электроника")
        self.good = make_good(self.category)
        self.promo = make_promo()

    def test_order_without_promo(self):
        response = self.client.post(
            ORDER_CREATE_URL, order_payload(self.good), format="json"
        )

        assert response.status_code == 201
        assert response.data["subtotal"] == "100.00"
        assert response.data["discount_rate"] == "0.0000"
        assert response.data["discount_amount"] == "0.00"
        assert response.data["total"] == "100.00"
        assert response.data["promo"] is None
        [item] = response.data["items"]
        assert item["good"] == self.good.pk
        assert item["unit_price"] == "100.00"
        assert item["total"] == "100.00"

    def test_order_with_promo_is_case_insensitive(self):
        response = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, promocode=" Welcome10 "),
            format="json",
        )

        assert response.status_code == 201
        assert response.data["discount_rate"] == "0.1000"
        assert response.data["discount_amount"] == "10.00"
        assert response.data["total"] == "90.00"
        assert response.data["promo"] == {
            "code": "WELCOME10",
            "discount_rate": "0.1000",
        }
        self.promo.refresh_from_db()
        assert self.promo.used_count == 1
        assert PromoRedemption.objects.filter(
            user=self.user, promo=self.promo
        ).exists()

    def test_promo_price_snapshot_is_taken_at_creation(self):
        self.client.post(
            ORDER_CREATE_URL, order_payload(self.good), format="json"
        )
        self.good.price = Decimal("999.00")
        self.good.save(update_fields=["price"])

        [item] = Order.objects.get().items.all()
        assert item.unit_price == Decimal("100.00")

    def test_promo_not_found(self):
        response = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, promocode="missing"),
            format="json",
        )

        assert response.status_code == 404

    def test_promo_inactive(self):
        make_promo(code="off10", is_active=False)

        response = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, promocode="off10"),
            format="json",
        )

        assert response.status_code == 400

    def test_promo_expired(self):
        make_promo(
            code="old10",
            expires_at=timezone.now() - timedelta(days=1),
        )

        response = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, promocode="old10"),
            format="json",
        )

        assert response.status_code == 400

    def test_promo_usage_limit_reached(self):
        make_promo(
            code="once5",
            discount_rate=Decimal("0.05"),
            max_uses=1,
            used_count=1,
        )

        response = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, promocode="once5"),
            format="json",
        )

        assert response.status_code == 409

    def test_promo_already_used_by_user(self):
        first = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, promocode="welcome10"),
            format="json",
        )
        assert first.status_code == 201

        response = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, promocode="welcome10"),
            format="json",
        )

        assert response.status_code == 409

    def test_promo_of_other_category_not_applicable(self):
        other_category = Category.objects.create(name="Книги")
        make_promo(code="books10", category=other_category)

        response = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, promocode="books10"),
            format="json",
        )

        assert response.status_code == 400

    def test_excluded_good_gets_no_discount(self):
        tv = make_good(self.category, name="Телевизор", price=Decimal("450.00"))
        cable = make_good(
            self.category,
            name="Кабель",
            price=Decimal("50.00"),
            is_promo_excluded=True,
        )

        response = self.client.post(
            ORDER_CREATE_URL,
            {
                "items": [
                    {"good": str(tv.pk), "quantity": 1},
                    {"good": str(cable.pk), "quantity": 1},
                ],
                "promocode": "welcome10",
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["subtotal"] == "500.00"
        assert response.data["discount_amount"] == "45.00"
        assert response.data["total"] == "455.00"
        items = {item["good_name"]: item for item in response.data["items"]}
        assert items["Телевизор"]["discount_amount"] == "45.00"
        assert items["Телевизор"]["discount_rate"] == "0.1000"
        assert items["Кабель"]["discount_amount"] == "0.00"
        assert items["Кабель"]["discount_rate"] == "0.0000"

    def test_all_goods_excluded_makes_promo_not_applicable(self):
        excluded = make_good(
            self.category, name="Исключение", is_promo_excluded=True
        )

        response = self.client.post(
            ORDER_CREATE_URL,
            {
                "items": [{"good": str(excluded.pk), "quantity": 1}],
                "promocode": "welcome10",
            },
            format="json",
        )

        assert response.status_code == 400

    def test_duplicate_goods_rejected(self):
        response = self.client.post(
            ORDER_CREATE_URL,
            {
                "items": [
                    {"good": str(self.good.pk), "quantity": 1},
                    {"good": str(self.good.pk), "quantity": 2},
                ],
            },
            format="json",
        )

        assert response.status_code == 400

    def test_empty_items_rejected(self):
        response = self.client.post(
            ORDER_CREATE_URL, {"items": []}, format="json"
        )

        assert response.status_code == 400

    def test_unknown_good_rejected(self):
        response = self.client.post(
            ORDER_CREATE_URL,
            {
                "items": [
                    {
                        "good": "8f0d1a52-0c6e-4a5d-9b1f-2e3a4b5c6d7e",
                        "quantity": 1,
                    }
                ]
            },
            format="json",
        )

        assert response.status_code == 400

    def test_blank_promocode_treated_as_absent(self):
        response = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, promocode="   "),
            format="json",
        )

        assert response.status_code == 201
        assert response.data["promo"] is None

    def test_unauthenticated_rejected(self):
        client = APIClient()

        response = client.post(
            ORDER_CREATE_URL, order_payload(self.good), format="json"
        )

        assert response.status_code == 401

    def test_idempotency_replay_returns_same_order(self):
        first = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, quantity=2),
            format="json",
            HTTP_IDEMPOTENCY_KEY="key-1",
        )
        assert first.status_code == 201

        second = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, quantity=2),
            format="json",
            HTTP_IDEMPOTENCY_KEY="key-1",
        )

        assert second.status_code == 200
        assert second.data["id"] == first.data["id"]
        assert Order.objects.count() == 1

    def test_idempotency_conflict_on_different_body(self):
        first = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, quantity=1),
            format="json",
            HTTP_IDEMPOTENCY_KEY="key-1",
        )
        assert first.status_code == 201

        second = self.client.post(
            ORDER_CREATE_URL,
            order_payload(self.good, quantity=2),
            format="json",
            HTTP_IDEMPOTENCY_KEY="key-1",
        )

        assert second.status_code == 409


@pytest.mark.django_db
class OrderListTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.other_user = make_user(email="other@example.com")
        self.category = Category.objects.create(name="Электроника")
        self.good = make_good(self.category)
        for buyer in (self.user, self.other_user):
            self.client.force_authenticate(user=buyer)
            response = self.client.post(
                ORDER_CREATE_URL, order_payload(self.good), format="json"
            )
            assert response.status_code == 201

    def test_user_sees_only_own_orders(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(ORDERS_LIST_URL)

        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["user"] == self.user.pk

    def test_admin_sees_all_orders(self):
        admin = make_user(
            email="admin@example.com", role=RoleChoices.ADMINISTRATOR
        )
        self.client.force_authenticate(user=admin)

        response = self.client.get(ORDERS_LIST_URL)

        assert response.status_code == 200
        assert len(response.data["results"]) == 2

    def test_order_retrieve(self):
        self.client.force_authenticate(user=self.user)
        [order] = Order.objects.filter(user=self.user)

        response = self.client.get(
            reverse("api_v1:api-root:order-detail", args=[order.pk])
        )

        assert response.status_code == 200
        assert response.data["total"] == "100.00"
        assert response.data["user"] == self.user.pk
