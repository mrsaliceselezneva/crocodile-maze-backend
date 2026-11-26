from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

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

        self.assertEqual(response.status_code, 403)

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
        client.get("/admin/login/")
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
