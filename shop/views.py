import logging

from django.db.models import Q
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from config.openapi import (
    ADMIN_ERRORS,
    BAD_REQUEST,
    OPTIONAL_AUTH,
    conflict,
    not_found,
    pk_param,
)

from .errors import Conflict, get_or_404
from .models import Brand, Category, Product
from .serializers import (
    BrandListSerializer,
    BrandSerializer,
    CategorySerializer,
    ProductFilterSerializer,
    ProductListSerializer,
    ProductSerializer,
)

logger = logging.getLogger(__name__)

PRODUCT_EXAMPLE = {
    "id": 1,
    "name": "Сухий корм для котів",
    "description": "З куркою, для дорослих котів",
    "price": 250.0,
    "animal_type": "cat",
    "weight": "2 кг",
    "stock": 15,
    "category_id": 1,
    "brand_id": 1,
}
PRODUCT_CREATE_EXAMPLE = {
    key: value for key, value in PRODUCT_EXAMPLE.items() if key != "id"
}


def save_or_400(serializer):
    serializer.is_valid(raise_exception=True)
    return serializer.save()


def log_change(request, action, kind, pk):
    logger.info("%s %s id=%s (user_id=%s)", action, kind, pk, request.user.pk)


class CategoryListView(APIView):
    @extend_schema(
        tags=["Categories"],
        summary="Список категорій",
        auth=OPTIONAL_AUTH,
        responses={200: CategorySerializer(many=True)},
    )
    def get(self, request):
        categories = Category.objects.order_by("id")
        return Response(CategorySerializer(categories, many=True).data)

    @extend_schema(
        tags=["Categories"],
        summary="Створити категорію",
        description="Лише адміністратор. Назва категорії унікальна.",
        request=CategorySerializer,
        responses={201: CategorySerializer, 400: BAD_REQUEST, **ADMIN_ERRORS},
    )
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        category = save_or_400(serializer)
        log_change(request, "Created", "Category", category.pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    @extend_schema(
        tags=["Categories"],
        summary="Одна категорія",
        auth=OPTIONAL_AUTH,
        parameters=[pk_param("id категорії")],
        responses={200: CategorySerializer, 404: not_found("Категорію")},
    )
    def get(self, request, pk):
        category = get_or_404(Category, pk, "Категорію")
        return Response(CategorySerializer(category).data)

    @extend_schema(
        tags=["Categories"],
        summary="Замінити категорію (PUT)",
        description="Лише адміністратор. PUT вимагає всі поля об'єкта.",
        parameters=[pk_param("id категорії")],
        request=CategorySerializer,
        responses={
            200: CategorySerializer,
            400: BAD_REQUEST,
            404: not_found("Категорію"),
            **ADMIN_ERRORS,
        },
    )
    def put(self, request, pk):
        category = get_or_404(Category, pk, "Категорію")
        serializer = CategorySerializer(category, data=request.data)
        save_or_400(serializer)
        log_change(request, "Updated", "Category", pk)
        return Response(serializer.data)

    @extend_schema(
        tags=["Categories"],
        summary="Частково змінити категорію (PATCH)",
        description="Лише адміністратор. PATCH змінює тільки передані поля.",
        parameters=[pk_param("id категорії")],
        request=CategorySerializer,
        responses={
            200: CategorySerializer,
            400: BAD_REQUEST,
            404: not_found("Категорію"),
            **ADMIN_ERRORS,
        },
    )
    def patch(self, request, pk):
        category = get_or_404(Category, pk, "Категорію")
        serializer = CategorySerializer(category, data=request.data, partial=True)
        save_or_400(serializer)
        log_change(request, "Updated", "Category", pk)
        return Response(serializer.data)

    @extend_schema(
        tags=["Categories"],
        summary="Видалити категорію",
        description="Лише адміністратор. Категорію з товарами видалити не можна.",
        parameters=[pk_param("id категорії")],
        responses={
            204: None,
            404: not_found("Категорію"),
            409: conflict(
                "Неможливо видалити категорію «Корм», оскільки в ній є товари: 3. "
                "Спочатку видаліть їх або перенесіть в іншу категорію."
            ),
            **ADMIN_ERRORS,
        },
    )
    def delete(self, request, pk):
        category = get_or_404(Category, pk, "Категорію")
        count = category.products.count()
        if count:
            logger.warning(
                "Delete of Category id=%s refused: %s product(s) linked (user_id=%s)",
                pk,
                count,
                request.user.pk,
            )
            raise Conflict(
                f"Неможливо видалити категорію «{category.name}», оскільки в ній "
                f"є товари: {count}. Спочатку видаліть їх або перенесіть в іншу "
                f"категорію."
            )
        category.delete()
        log_change(request, "Deleted", "Category", pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryProductsView(APIView):
    @extend_schema(
        tags=["Categories"],
        summary="Товари категорії",
        auth=OPTIONAL_AUTH,
        parameters=[pk_param("id категорії")],
        responses={200: ProductListSerializer(many=True), 404: not_found("Категорію")},
    )
    def get(self, request, pk):
        category = get_or_404(Category, pk, "Категорію")
        products = category.products.order_by("id")
        return Response(ProductListSerializer(products, many=True).data)


class BrandListView(APIView):
    @extend_schema(
        tags=["Brands"],
        summary="Список брендів",
        auth=OPTIONAL_AUTH,
        responses={200: BrandListSerializer(many=True)},
    )
    def get(self, request):
        brands = Brand.objects.order_by("id")
        return Response(BrandListSerializer(brands, many=True).data)

    @extend_schema(
        tags=["Brands"],
        summary="Додати бренд",
        description="Лише адміністратор. Назва бренду унікальна.",
        request=BrandSerializer,
        responses={201: BrandSerializer, 400: BAD_REQUEST, **ADMIN_ERRORS},
    )
    def post(self, request):
        serializer = BrandSerializer(data=request.data)
        brand = save_or_400(serializer)
        log_change(request, "Created", "Brand", brand.pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BrandDetailView(APIView):
    @extend_schema(
        tags=["Brands"],
        summary="Один бренд",
        auth=OPTIONAL_AUTH,
        parameters=[pk_param("id бренду")],
        responses={200: BrandSerializer, 404: not_found("Бренд")},
    )
    def get(self, request, pk):
        brand = get_or_404(Brand, pk, "Бренд")
        return Response(BrandSerializer(brand).data)

    @extend_schema(
        tags=["Brands"],
        summary="Замінити бренд (PUT)",
        description="Лише адміністратор. PUT вимагає всі обов'язкові поля.",
        parameters=[pk_param("id бренду")],
        request=BrandSerializer,
        responses={
            200: BrandSerializer,
            400: BAD_REQUEST,
            404: not_found("Бренд"),
            **ADMIN_ERRORS,
        },
    )
    def put(self, request, pk):
        brand = get_or_404(Brand, pk, "Бренд")
        serializer = BrandSerializer(brand, data=request.data)
        save_or_400(serializer)
        log_change(request, "Updated", "Brand", pk)
        return Response(serializer.data)

    @extend_schema(
        tags=["Brands"],
        summary="Частково змінити бренд (PATCH)",
        description="Лише адміністратор. PATCH змінює тільки передані поля.",
        parameters=[pk_param("id бренду")],
        request=BrandSerializer,
        responses={
            200: BrandSerializer,
            400: BAD_REQUEST,
            404: not_found("Бренд"),
            **ADMIN_ERRORS,
        },
    )
    def patch(self, request, pk):
        brand = get_or_404(Brand, pk, "Бренд")
        serializer = BrandSerializer(brand, data=request.data, partial=True)
        save_or_400(serializer)
        log_change(request, "Updated", "Brand", pk)
        return Response(serializer.data)

    @extend_schema(
        tags=["Brands"],
        summary="Видалити бренд",
        description="Лише адміністратор. Бренд із товарами видалити не можна.",
        parameters=[pk_param("id бренду")],
        responses={
            204: None,
            404: not_found("Бренд"),
            409: conflict(
                "Неможливо видалити бренд «Royal Canin», оскільки за ним "
                "закріплено товарів: 3. Спочатку видаліть їх або змініть їм бренд."
            ),
            **ADMIN_ERRORS,
        },
    )
    def delete(self, request, pk):
        brand = get_or_404(Brand, pk, "Бренд")
        count = brand.products.count()
        if count:
            logger.warning(
                "Delete of Brand id=%s refused: %s product(s) linked (user_id=%s)",
                pk,
                count,
                request.user.pk,
            )
            raise Conflict(
                f"Неможливо видалити бренд «{brand.name}», оскільки за ним "
                f"закріплено товарів: {count}. Спочатку видаліть їх або змініть "
                f"їм бренд."
            )
        brand.delete()
        log_change(request, "Deleted", "Brand", pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class BrandProductsView(APIView):
    @extend_schema(
        tags=["Brands"],
        summary="Товари бренду",
        auth=OPTIONAL_AUTH,
        parameters=[pk_param("id бренду")],
        responses={200: ProductListSerializer(many=True), 404: not_found("Бренд")},
    )
    def get(self, request, pk):
        brand = get_or_404(Brand, pk, "Бренд")
        products = brand.products.order_by("id")
        return Response(ProductListSerializer(products, many=True).data)


def case_variants(text):
    return {text, text.lower(), text.upper(), text.capitalize(), text.title()}


class ProductListView(APIView):
    @extend_schema(
        tags=["Products"],
        summary="Каталог товарів (пошук, фільтри, сортування)",
        description=(
            "Усі параметри необов'язкові й комбінуються. Приклад: "
            "`GET /api/products?animal_type=cat&category=1&max_price=500"
            "&sort=price_asc`."
        ),
        auth=OPTIONAL_AUTH,
        parameters=[ProductFilterSerializer],
        responses={200: ProductListSerializer(many=True), 400: BAD_REQUEST},
        examples=[
            OpenApiExample(
                "Список товарів",
                value=[
                    {
                        "id": 1,
                        "name": "Сухий корм для котів",
                        "price": 250.0,
                        "animal_type": "cat",
                        "category_id": 1,
                        "brand_id": 1,
                    }
                ],
                response_only=True,
                status_codes=["200"],
            )
        ],
    )
    def get(self, request):
        filters = ProductFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        params = filters.validated_data
        logger.debug("Product list requested with filters: %s", dict(params))

        products = Product.objects.all()

        search = params.get("search", "").strip()
        if search:
            query = Q()
            for variant in case_variants(search):
                query |= Q(name__icontains=variant)
                query |= Q(brand__name__icontains=variant)
            products = products.filter(query)
        if "animal_type" in params:
            products = products.filter(animal_type=params["animal_type"])
        if "category" in params:
            products = products.filter(category_id=params["category"])
        if "brand" in params:
            products = products.filter(brand_id=params["brand"])
        if "min_price" in params:
            products = products.filter(price__gte=params["min_price"])
        if "max_price" in params:
            products = products.filter(price__lte=params["max_price"])

        ordering = {"price_asc": "price", "price_desc": "-price"}
        products = products.order_by(ordering.get(params.get("sort"), "id"), "id")

        return Response(ProductListSerializer(products, many=True).data)

    @extend_schema(
        tags=["Products"],
        summary="Додати товар",
        description=(
            "Лише адміністратор. `name`, `price`, `animal_type`, `category_id` "
            "і `brand_id` обов'язкові; ціна більша за 0, `stock` не від'ємний, "
            "категорія і бренд мають існувати."
        ),
        request=ProductSerializer,
        responses={201: ProductSerializer, 400: BAD_REQUEST, **ADMIN_ERRORS},
        examples=[
            OpenApiExample(
                "Новий товар", value=PRODUCT_CREATE_EXAMPLE, request_only=True
            ),
            OpenApiExample(
                "Створений товар",
                value=PRODUCT_EXAMPLE,
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        product = save_or_400(serializer)
        log_change(request, "Created", "Product", product.pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProductDetailView(APIView):
    @extend_schema(
        tags=["Products"],
        summary="Один товар",
        auth=OPTIONAL_AUTH,
        parameters=[pk_param("id товару")],
        responses={200: ProductSerializer, 404: not_found("Товар")},
        examples=[
            OpenApiExample(
                "Товар",
                value=PRODUCT_EXAMPLE,
                response_only=True,
                status_codes=["200"],
            )
        ],
    )
    def get(self, request, pk):
        product = get_or_404(Product, pk, "Товар")
        return Response(ProductSerializer(product).data)

    @extend_schema(
        tags=["Products"],
        summary="Замінити товар (PUT)",
        description=(
            "Лише адміністратор. PUT вимагає всі обов'язкові поля товару "
            "(як при створенні)."
        ),
        parameters=[pk_param("id товару")],
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: BAD_REQUEST,
            404: not_found("Товар"),
            **ADMIN_ERRORS,
        },
        examples=[
            OpenApiExample(
                "Повна заміна", value=PRODUCT_CREATE_EXAMPLE, request_only=True
            )
        ],
    )
    def put(self, request, pk):
        product = get_or_404(Product, pk, "Товар")
        serializer = ProductSerializer(product, data=request.data)
        save_or_400(serializer)
        log_change(request, "Updated", "Product", pk)
        return Response(serializer.data)

    @extend_schema(
        tags=["Products"],
        summary="Частково змінити товар (PATCH)",
        description="Лише адміністратор. PATCH змінює тільки передані поля.",
        parameters=[pk_param("id товару")],
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: BAD_REQUEST,
            404: not_found("Товар"),
            **ADMIN_ERRORS,
        },
        examples=[
            OpenApiExample(
                "Змінити ціну і залишок",
                value={"price": 275.0, "stock": 10},
                request_only=True,
            )
        ],
    )
    def patch(self, request, pk):
        product = get_or_404(Product, pk, "Товар")
        serializer = ProductSerializer(product, data=request.data, partial=True)
        save_or_400(serializer)
        log_change(request, "Updated", "Product", pk)
        return Response(serializer.data)

    @extend_schema(
        tags=["Products"],
        summary="Видалити товар",
        description="Лише адміністратор.",
        parameters=[pk_param("id товару")],
        responses={204: None, 404: not_found("Товар"), **ADMIN_ERRORS},
    )
    def delete(self, request, pk):
        product = get_or_404(Product, pk, "Товар")
        product.delete()
        log_change(request, "Deleted", "Product", pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(exclude=True)
class UnknownEndpointView(APIView):
    def initial(self, request, *args, **kwargs):
        raise NotFound("Такого ендпоінта не існує.")
