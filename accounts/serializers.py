from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

PASSWORD_MIN_LENGTH = 8
# Верхня межа потрібна, щоб не змушувати сервер хешувати гігантські рядки.
PASSWORD_MAX_LENGTH = 128


class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=150,
        validators=[
            UnicodeUsernameValidator(),
            UniqueValidator(
                queryset=User.objects.all(),
                lookup="iexact",
                message="Користувач з таким username вже існує.",
            ),
        ],
    )
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(
        max_length=254,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                lookup="iexact",
                message="Користувач з таким email вже існує.",
            )
        ],
    )
    password = serializers.CharField(
        write_only=True,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        max_length=PASSWORD_MAX_LENGTH,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "password_confirm",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Паролі не збігаються."}
            )

        # Складність пароля: не надто поширений, не суто цифровий і не схожий
        # на дані користувача (див. AUTH_PASSWORD_VALIDATORS у settings.py).
        candidate = User(
            username=attrs["username"],
            email=attrs["email"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        # create_user хешує пароль (PBKDF2), у БД він ніколи не лежить у відкритому
        # вигляді.
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "is_staff"]
        read_only_fields = fields


class LoginSerializer(TokenObtainPairSerializer):
    """Перевіряє username + password і повертає пару токенів та дані користувача."""

    default_error_messages = {"no_active_account": "Невірний username або пароль."}

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
