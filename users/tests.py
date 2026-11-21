from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Role, User


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
