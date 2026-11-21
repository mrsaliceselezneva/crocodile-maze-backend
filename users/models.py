from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class Role(models.Model):
    class Code(models.TextChoices):
        ADMIN = "ADMIN", "Администратор"
        STUDENT = "STUDENT", "Ученик"

    code = models.CharField(
        max_length=16,
        choices=Code.choices,
        unique=True,
    )

    def __str__(self) -> str:
        return self.get_code_display()


class MazeUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        if "role" not in extra_fields and "role_id" not in extra_fields:
            extra_fields["role"] = Role.objects.using(self.db).get(code=Role.Code.ADMIN)

        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="assigned_users",
        null=True,
    )
    objects = MazeUserManager()
