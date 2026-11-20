from django.contrib.auth.models import AbstractUser
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


class User(AbstractUser):
    roles = models.ManyToManyField(
        Role,
        related_name="users",
        blank=True,
    )
