import os

import pytest


os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-production")


TEST_PASSWORD = "Str0ng-pass-42"


@pytest.fixture
def password():
    return TEST_PASSWORD


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def regular_user(db, password):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        username="olena", email="olena@example.com", password=password
    )


@pytest.fixture
def staff_user(db, password):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        username="manager",
        email="manager@example.com",
        password=password,
        is_staff=True,
    )


def make_authenticated_client(user):
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import AccessToken

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


@pytest.fixture
def user_client(regular_user):
    return make_authenticated_client(regular_user)


@pytest.fixture
def staff_client(staff_user):
    return make_authenticated_client(staff_user)


@pytest.fixture
def category(db):
    from shop.models import Category

    return Category.objects.create(name="Корм")


@pytest.fixture
def brand(db):
    from shop.models import Brand

    return Brand.objects.create(name="Royal Canin", country="Франція")


@pytest.fixture
def make_product(db, category, brand):
    from shop.models import Product

    def factory(**overrides):
        data = {
            "name": "Корм для котів",
            "price": "250.00",
            "animal_type": "cat",
            "stock": 5,
            "category": category,
            "brand": brand,
        }
        data.update(overrides)
        return Product.objects.create(**data)

    return factory


@pytest.fixture
def product(make_product):
    return make_product()


@pytest.fixture
def product_payload(category, brand):
    return {
        "name": "Лежак",
        "description": "М'який",
        "price": 799.5,
        "animal_type": "dog",
        "weight": "2 кг",
        "stock": 3,
        "category_id": category.pk,
        "brand_id": brand.pk,
    }
