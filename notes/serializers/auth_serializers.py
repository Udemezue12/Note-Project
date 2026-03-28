import phonenumbers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from ..crud_deps import crud_actions

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "password",
            "confirm_password",
        ]

    def validate_email(self, value):
        if crud_actions.exists(model=User, email=value):
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_first_name(self, value):
        if not value.replace(" ", "").isalpha():
            raise serializers.ValidationError(
                "First name must only contain letters and spaces"
            )
        return value

    def validate_last_name(self, value):
        if not value.replace(" ", "").isalpha():
            raise serializers.ValidationError(
                "Last name must only contain letters and spaces"
            )
        return value

    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match"}
            )

        validate_password(password)

        return attrs

    def validate_phone_number(self, value):
        try:
            parsed = phonenumbers.parse(value, None)

            if not phonenumbers.is_valid_number(parsed):
                raise serializers.ValidationError(
                    "Invalid phone number. Use full international format."
                )

            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )

        except Exception:
            raise serializers.ValidationError(
                "Invalid phone number format. Use e.g. +2348012345678"
            )

    def validate_username(self, value):
        if crud_actions.exists(User, username=value):
            raise serializers.ValidationError("Username already exists")
        return value


class LoginSerializer(serializers.Serializer):

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):

        if not attrs.get("username"):
            raise serializers.ValidationError(
                {"username": "Username is required"})

        if not attrs.get("password"):
            raise serializers.ValidationError(
                {"password": "Password is required"})

        return attrs


class ResendEmail(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not crud_actions.exists(User, email=value):
            raise serializers.ValidationError("Email doesn't exists")
        return value


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(required=False)
    otp = serializers.CharField(required=False)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not crud_actions.exists(User, email=value):
            raise serializers.ValidationError("Email doesn't exists")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(required=False)
    otp = serializers.CharField(required=False)
    new_password = serializers.CharField()
