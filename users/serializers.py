from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from psycopg2.errors import UniqueViolation
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Role, User


class CurrentUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.code", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "role")


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class RegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    username = serializers.CharField(
        label="Хендл Codeforces",
        max_length=150,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                lookup="iexact",
                message="Этот хендл уже занят.",
            ),
        ],
    )
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        candidate = User(
            username=attrs["username"],
            first_name=attrs["first_name"],
            last_name=attrs["last_name"],
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc

        return attrs

    def create(self, validated_data):
        guest = Role.objects.get(code=Role.Code.GUEST)

        try:
            with transaction.atomic():
                return User.objects.create_user(
                    username=validated_data["username"],
                    first_name=validated_data["first_name"],
                    last_name=validated_data["last_name"],
                    password=validated_data["password"],
                    role=guest,
                )
        except IntegrityError as exc:
            cause = exc.__cause__
            if isinstance(cause, UniqueViolation) and cause.diag.constraint_name in {
                "users_user_username_key",
                "users_username_lower_unique",
            }:
                raise serializers.ValidationError(
                    {"username": ["Этот хендл уже занят."]}
                ) from exc
            raise


class AccessTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)


class DetailErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


class RegistrationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name")
