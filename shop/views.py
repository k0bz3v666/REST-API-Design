from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

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


def save_or_400(serializer):
    serializer.is_valid(raise_exception=True)
    return serializer.save()


class CategoryListView(APIView):
    def get(self, request):
        categories = Category.objects.order_by("id")
        return Response(CategorySerializer(categories, many=True).data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        save_or_400(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    def get(self, request, pk):
        category = get_or_404(Category, pk, "Категорію")
        return Response(CategorySerializer(category).data)

    def put(self, request, pk):
        category = get_or_404(Category, pk, "Категорію")
        serializer = CategorySerializer(category, data=request.data)
        save_or_400(serializer)
        return Response(serializer.data)

    def patch(self, request, pk):
        category = get_or_404(Category, pk, "Категорію")
        serializer = CategorySerializer(category, data=request.data, partial=True)
        save_or_400(serializer)
        return Response(serializer.data)

    def delete(self, request, pk):
        category = get_or_404(Category, pk, "Категорію")
        count = category.products.count()
        if count:
            raise Conflict(
                f"Неможливо видалити категорію «{category.name}», оскільки в ній "
                f"є товари: {count}. Спочатку видаліть їх або перенесіть в іншу "
                f"категорію."
            )
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryProductsView(APIView):
    def get(self, request, pk):
        category = get_or_404(Category, pk, "Категорію")
        products = category.products.order_by("id")
        return Response(ProductListSerializer(products, many=True).data)


class BrandListView(APIView):
    def get(self, request):
        brands = Brand.objects.order_by("id")
        return Response(BrandListSerializer(brands, many=True).data)

    def post(self, request):
        serializer = BrandSerializer(data=request.data)
        save_or_400(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BrandDetailView(APIView):
    def get(self, request, pk):
        brand = get_or_404(Brand, pk, "Бренд")
        return Response(BrandSerializer(brand).data)

    def put(self, request, pk):
        brand = get_or_404(Brand, pk, "Бренд")
        serializer = BrandSerializer(brand, data=request.data)
        save_or_400(serializer)
        return Response(serializer.data)

    def patch(self, request, pk):
        brand = get_or_404(Brand, pk, "Бренд")
        serializer = BrandSerializer(brand, data=request.data, partial=True)
        save_or_400(serializer)
        return Response(serializer.data)

    def delete(self, request, pk):
        brand = get_or_404(Brand, pk, "Бренд")
        count = brand.products.count()
        if count:
            raise Conflict(
                f"Неможливо видалити бренд «{brand.name}», оскільки за ним "
                f"закріплено товарів: {count}. Спочатку видаліть їх або змініть "
                f"їм бренд."
            )
        brand.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BrandProductsView(APIView):
    def get(self, request, pk):
        brand = get_or_404(Brand, pk, "Бренд")
        products = brand.products.order_by("id")
        return Response(ProductListSerializer(products, many=True).data)


def case_variants(text):
    return {text, text.lower(), text.upper(), text.capitalize(), text.title()}


class ProductListView(APIView):
    def get(self, request):
        filters = ProductFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        params = filters.validated_data

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

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        save_or_400(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProductDetailView(APIView):
    def get(self, request, pk):
        product = get_or_404(Product, pk, "Товар")
        return Response(ProductSerializer(product).data)

    def put(self, request, pk):
        product = get_or_404(Product, pk, "Товар")
        serializer = ProductSerializer(product, data=request.data)
        save_or_400(serializer)
        return Response(serializer.data)

    def patch(self, request, pk):
        product = get_or_404(Product, pk, "Товар")
        serializer = ProductSerializer(product, data=request.data, partial=True)
        save_or_400(serializer)
        return Response(serializer.data)

    def delete(self, request, pk):
        product = get_or_404(Product, pk, "Товар")
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UnknownEndpointView(APIView):
    def initial(self, request, *args, **kwargs):
        raise NotFound("Такого ендпоінта не існує.")
