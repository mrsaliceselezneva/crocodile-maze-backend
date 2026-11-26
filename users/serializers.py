from rest_framework import serializers

from .models import User


class CurrentUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.code", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "role")


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class AccessTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)


class DetailErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
