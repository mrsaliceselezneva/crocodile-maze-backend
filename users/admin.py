from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class MazeUserAdmin(UserAdmin):
    role_fields = (
        ("Роли в Crocodile Maze", {"fields": ("roles",)}),
    )

    fieldsets = UserAdmin.fieldsets + role_fields
    add_fieldsets = UserAdmin.add_fieldsets + role_fields
    filter_horizontal = UserAdmin.filter_horizontal + ("roles",)
