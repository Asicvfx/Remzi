from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AuthApiTests(APITestCase):
    def test_register_user(self):
        payload = {
            "username": "remzi-user",
            "email": "user@example.com",
            "password": "StrongPass123",
            "password_confirm": "StrongPass123",
            "first_name": "Remzi",
            "last_name": "Tester",
        }

        response = self.client.post(reverse("users:register"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="remzi-user").exists())

    def test_login_returns_tokens(self):
        user = User.objects.create_user(
            username="login-user",
            email="login@example.com",
            password="StrongPass123",
        )

        response = self.client.post(
            reverse("users:login"),
            {"username": user.username, "password": "StrongPass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], user.username)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("users:me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        user = User.objects.create_user(
            username="profile-user",
            email="profile@example.com",
            password="StrongPass123",
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("users:me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], user.email)
