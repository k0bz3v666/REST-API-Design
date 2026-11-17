from rest_framework import serializers

from .serializers import UserSerializer


class CredentialsSerializer(serializers.Serializer):
    username = serializers.CharField(help_text="Ім'я користувача.")
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}, help_text="Пароль."
    )


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(
        help_text="Access токен (живе недовго), передається в Authorization: Bearer."
    )
    refresh = serializers.CharField(
        help_text="Refresh токен, потрібен лише для POST /api/auth/refresh."
    )
    user = UserSerializer(help_text="Дані користувача (is_staff — чи він адміністратор).")


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="Refresh токен, отриманий при логіні.")


class AccessTokenSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="Новий access токен.")
