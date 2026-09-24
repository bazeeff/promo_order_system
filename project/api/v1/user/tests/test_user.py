from unittest import TestCase

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
class UserRegistrationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse(
            "api_v1:api-root:user-registration"
        )  # Используем имя маршрута для регистрации
        self.registration_data = {
            "first_name": "Тест",
            "email": "testuser@example.com",
            "password": "123456789",
            "password2": "123456789",
        }

    def test_registration(self):
        print(self.registration_data, flush=True)
        response = self.client.post(self.url, self.registration_data, format="json")
        self.assertEqual(
            response.status_code, 201
        )  # Проверяем, что статус - 201 Created
        self.assertIn("id", response.data)  # Проверяем, что вернулся id пользователя
        self.assertEqual(
            response.data["first_name"], self.registration_data["first_name"]
        )  # Проверяем, что имя пользователя правильное


@pytest.mark.django_db
class UserLoginTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.registration_url = reverse(
            "api_v1:api-root:user-registration"
        )  # Маршрут для регистрации
        self.login_url = reverse("api_v1:api-root:user-login")  # Маршрут для логина

        # Регистрируем пользователя
        self.client.post(
            self.registration_url,
            {
                "first_name": "Тест",
                "email": "testuser@example.com",
                "password": "123456789",
                "password2": "123456789",
            },
            format="json",
        )

    def test_login(self):
        login_data = {
            "email": "testuser@example.com",
            "password": "123456789",
        }
        response = self.client.post(self.login_url, login_data, format="json")
        self.assertEqual(response.status_code, 200)  # Проверяем статус 200
        self.assertIn("access", response.data)  # Проверяем наличие токенов
        self.assertIn("refresh", response.data)
