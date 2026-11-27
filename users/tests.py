from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User, Role


class SuperuserTests(TestCase):
    def test_createsuperuser_assigns_admin_role(self):
        call_command(
            "createsuperuser",
            username="test_admin",
            email="admin@example.com",
            interactive=False,
            verbosity=0,
        )

        user = User.objects.get(username="test_admin")
        self.assertEqual(user.role.code, Role.Code.ADMIN)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)


class UserRoleTests(TestCase):
    def test_cannot_create_user_without_role(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="without_role")


class CurrentUserTests(TestCase):
    def test_anonymous_user_cannot_read_profile(self):
        response = self.client.get(reverse("current-user"))

        self.assertEqual(response.status_code, 401)

    def test_student_can_read_own_profile(self):
        student = User.objects.create_user(
            username="maze_runner",
            role=Role.objects.get(code=Role.Code.STUDENT),
        )
        self.client.force_login(student)

        response = self.client.get(reverse("current-user"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": student.pk, "username": "maze_runner", "role": "STUDENT"},
        )


class LoginTests(TestCase):
    def test_login_returns_access_and_sets_refresh_cookie(self):
        password = "MazeTest42!"
        User.objects.create_superuser(
            username="test_admin",
            email="admin@example.com",
            password=password,
        )

        client = Client(enforce_csrf_checks=True)
        csrf_response = client.get("/api/auth/csrf/")
        self.assertEqual(csrf_response.status_code, 204)
        self.assertIn("csrftoken", csrf_response.cookies)
        response = client.post(
            "/api/auth/login/",
            {"username": "test_admin", "password": password},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["access"])
        self.assertNotIn("refresh", response.json())

        refresh = response.cookies["refresh"]
        self.assertTrue(refresh.value)
        self.assertTrue(refresh["httponly"])
        self.assertEqual(refresh["max-age"], 31 * 24 * 60 * 60)

        access = response.json()["access"]
        profile = Client().get(
            "/api/auth/me/",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )

        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["username"], "test_admin")
        self.assertEqual(profile.json()["role"], "ADMIN")

        old_refresh = refresh.value
        csrf = client.cookies["csrftoken"].value

        renewed = client.post("/api/auth/refresh/", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(renewed.status_code, 200)
        self.assertTrue(renewed.json()["access"])
        self.assertNotIn("refresh", renewed.json())
        self.assertNotEqual(renewed.cookies["refresh"].value, old_refresh)
        self.assertEqual(renewed.cookies["refresh"]["max-age"], 31 * 24 * 60 * 60)

        client.cookies["refresh"] = old_refresh
        repeated = client.post("/api/auth/refresh/", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(repeated.status_code, 401)

    def test_logout_revokes_refresh_and_ends_session(self):
        student = User.objects.create_user(
            username="logout_student",
            role=Role.objects.get(code=Role.Code.STUDENT),
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(student)
        client.get("/api/auth/csrf/")
        csrf = client.cookies["csrftoken"].value
        saved_refresh = str(RefreshToken.for_user(student))
        client.cookies["refresh"] = saved_refresh

        self.assertEqual(client.post("/api/auth/logout/").status_code, 403)

        response = client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.cookies["refresh"]["max-age"], 0)
        self.assertEqual(response.cookies["refresh"]["path"], "/api/auth/")
        self.assertEqual(client.get("/api/auth/me/").status_code, 401)

        client.cookies["refresh"] = saved_refresh
        retry = client.post("/api/auth/refresh/", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(retry.status_code, 401)

    def test_inactive_student_cannot_log_in(self):
        password = "MazeTest42!"
        student = User.objects.create_user(
            username="inactive_student",
            password=password,
            is_active=False,
            role=Role.objects.get(code=Role.Code.STUDENT),
        )

        client = Client(enforce_csrf_checks=True)
        client.get("/api/auth/csrf/")
        response = client.post(
            "/api/auth/login/",
            {"username": student.username, "password": password},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("access", response.json())
        self.assertNotIn("refresh", response.cookies)

    def test_token_expiration(self):
        student = User.objects.create_user(
            username="expiry_student",
            role=Role.objects.get(code=Role.Code.STUDENT),
        )
        client = Client(enforce_csrf_checks=True)
        client.get("/api/auth/csrf/")
        csrf = client.cookies["csrftoken"].value
        now = timezone.now()

        # Через 16 минут access уже истёк, а refresh ещё действует.
        with patch("rest_framework_simplejwt.tokens.aware_utcnow",
                   return_value=now - timedelta(minutes=16)):
            refresh = RefreshToken.for_user(student)
            access = str(refresh.access_token)

        profile = client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(profile.status_code, 401)

        client.cookies["refresh"] = str(refresh)
        renewed = client.post("/api/auth/refresh/", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(renewed.status_code, 200)

        new_refresh = RefreshToken(renewed.cookies["refresh"].value)
        self.assertGreaterEqual(new_refresh["iat"], int(now.timestamp()))
        self.assertEqual(new_refresh["exp"] - new_refresh["iat"], 31 * 24 * 60 * 60)

        # После 32 дней без обновления истёк и сам refresh.
        with patch("rest_framework_simplejwt.tokens.aware_utcnow",
                   return_value=now - timedelta(days=32)):
            expired_refresh = RefreshToken.for_user(student)

        client.cookies["refresh"] = str(expired_refresh)
        denied = client.post("/api/auth/refresh/", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(denied.status_code, 401)
        self.assertNotIn("access", denied.json())


class UsernameTests(TestCase):
    def test_handle_is_unique_regardless_of_case(self):
        guest = Role.objects.get(code=Role.Code.GUEST)
        User.objects.create_user(username="MazeRunner", role=guest)

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="mazerunner", role=guest)
