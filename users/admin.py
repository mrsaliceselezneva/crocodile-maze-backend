from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class MazeUserAdmin(UserAdmin):
    role_fields = (
        ("Роль в Crocodile Maze", {"fields": ("role",)}),
    )

    fieldsets = UserAdmin.fieldsets + role_fields
    add_fieldsets = UserAdmin.add_fieldsets + role_fields
