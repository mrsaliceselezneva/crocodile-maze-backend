from rest_framework.permissions import BasePermission

from .models import Role


class IsMazeAdmin(BasePermission):
    message = "Доступ разрешён только администратору."

    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.role.code == Role.Code.ADMIN
