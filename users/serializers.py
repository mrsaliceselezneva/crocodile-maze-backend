from rest_framework import serializers

from .models import User


class CurrentUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.code", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "role")
