from decimal import Decimal

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Brand, Category, Product


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=100,
        validators=[
            UniqueValidator(
                queryset=Category.objects.all(),
                message="Категорія з такою назвою вже існує.",
            )
        ],
    )

    class Meta:
        model = Category
        fields = ["id", "name"]


class BrandSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=100,
        validators=[
            UniqueValidator(
                queryset=Brand.objects.all(),
                message="Бренд з такою назвою вже існує.",
            )
        ],
    )

    class Meta:
        model = Brand
        fields = ["id", "name", "description", "country"]


class BrandListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name"]


class ProductSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
        error_messages={"does_not_exist": "Категорії з id={pk_value} не існує."},
    )
    brand_id = serializers.PrimaryKeyRelatedField(
        source="brand",
        queryset=Brand.objects.all(),
        error_messages={"does_not_exist": "Бренду з id={pk_value} не існує."},
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "animal_type",
            "weight",
            "stock",
            "category_id",
            "brand_id",
        ]


class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "price", "animal_type", "category_id", "brand_id"]


class ProductFilterSerializer(serializers.Serializer):
    SORT_CHOICES = ["price_asc", "price_desc"]

    search = serializers.CharField(required=False, allow_blank=True)
    animal_type = serializers.ChoiceField(
        choices=Product.AnimalType.choices, required=False
    )
    category = serializers.IntegerField(required=False, min_value=1)
    brand = serializers.IntegerField(required=False, min_value=1)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, min_value=Decimal("0")
    )
    max_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, min_value=Decimal("0")
    )
    sort = serializers.ChoiceField(choices=SORT_CHOICES, required=False)

    def validate(self, attrs):
        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise serializers.ValidationError(
                "min_price не може бути більшим за max_price."
            )
        return attrs
