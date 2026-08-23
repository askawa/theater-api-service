from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class UserApiTests(APITestCase):
    def test_user_can_register_and_receive_tokens(self):
        payload = {
            "email": "visitor@example.com",
            "password": "secure-pass-123",
            "first_name": "Ada",
            "last_name": "Lovelace",
        }

        register_response = self.client.post(reverse("user:register"), payload)
        token_response = self.client.post(
            reverse("user:token_obtain_pair"),
            {"email": payload["email"], "password": payload["password"]},
        )

        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", register_response.data)
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", token_response.data)
        self.assertIn("refresh", token_response.data)

    def test_authenticated_user_can_update_profile(self):
        user = get_user_model().objects.create_user(
            email="profile@example.com",
            password="secure-pass-123",
        )
        self.client.force_authenticate(user)

        response = self.client.patch(
            reverse("user:manage"),
            {"first_name": "Grace"},
        )

        user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user.first_name, "Grace")

    def test_profile_requires_authentication(self):
        response = self.client.get(reverse("user:manage"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

