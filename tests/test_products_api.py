from datetime import timedelta

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from shop.models import Category, Product

pytestmark = pytest.mark.django_db

LIST_URL = "/api/products"

LIST_FIELDS = {"id", "name", "price", "animal_type", "category_id", "brand_id"}
DETAIL_FIELDS = LIST_FIELDS | {"description", "weight", "stock"}


def detail_url(pk):
    return f"{LIST_URL}/{pk}"


def assert_error(response, status_code):
    assert response.status_code == status_code, response.content
    body = response.json()
    assert isinstance(body["error"], str) and body["error"]
    return body


class TestRead:
    def test_anonymous_can_list_products(self, api_client, make_product):
        make_product(name="Перший")
        make_product(name="Другий")

        response = api_client.get(LIST_URL)

        assert response.status_code == 200
        items = response.json()
        assert [item["name"] for item in items] == ["Перший", "Другий"]
        assert set(items[0]) == LIST_FIELDS

    def test_empty_catalog_returns_empty_list(self, api_client):
        response = api_client.get(LIST_URL)

        assert response.status_code == 200
        assert response.json() == []

    def test_retrieve_returns_full_product(self, api_client, product):
        response = api_client.get(detail_url(product.pk))

        assert response.status_code == 200
        body = response.json()
        assert set(body) == DETAIL_FIELDS
        assert body["name"] == "Корм для котів"
        assert body["price"] == 250.0
        assert body["category_id"] == product.category_id
        assert body["brand_id"] == product.brand_id

    def test_retrieve_missing_product_is_404(self, api_client):
        body = assert_error(api_client.get(detail_url(999)), 404)

        assert body["error"] == "Товар з id=999 не знайдено."

    def test_regular_user_can_read(self, user_client, product):
        assert user_client.get(LIST_URL).status_code == 200
        assert user_client.get(detail_url(product.pk)).status_code == 200

    def test_invalid_token_is_rejected_even_for_read(self, product):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")

        assert_error(client.get(LIST_URL), 401)


class TestFilteringAndSorting:
    @pytest.fixture
    def catalog(self, make_product):
        toys = Category.objects.create(name="Іграшки")
        make_product(name="Дешевий", price="100")
        make_product(name="Дорогий", price="900", animal_type="dog")
        make_product(name="М'ячик", price="50", category=toys)
        return {"toys": toys}

    def names(self, client, query=""):
        response = client.get(f"{LIST_URL}?{query}")
        assert response.status_code == 200
        return [item["name"] for item in response.json()]

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("", ["Дешевий", "Дорогий", "М'ячик"]),
            ("animal_type=dog", ["Дорогий"]),
            ("min_price=100&sort=price_desc", ["Дорогий", "Дешевий"]),
            ("max_price=100&sort=price_asc", ["М'ячик", "Дешевий"]),
            ("sort=price_desc", ["Дорогий", "Дешевий", "М'ячик"]),
            ("search=дорогий", ["Дорогий"]),
            ("search=royal", ["Дешевий", "Дорогий", "М'ячик"]),
            ("search=нічого-такого", []),
        ],
    )
    def test_query_params(self, api_client, catalog, query, expected):
        assert self.names(api_client, query) == expected

    def test_filter_by_category_and_brand(self, api_client, catalog, brand):
        toys = catalog["toys"]

        assert self.names(api_client, f"category={toys.pk}") == ["М'ячик"]
        assert self.names(api_client, f"brand={brand.pk}&category={toys.pk}") == [
            "М'ячик"
        ]
        assert self.names(api_client, "brand=999") == []

    @pytest.mark.parametrize(
        "query",
        [
            "sort=popular",
            "animal_type=dragon",
            "min_price=abc",
            "category=x",
            "category=0",
            "min_price=-1",
            "min_price=10&max_price=5",
        ],
    )
    def test_invalid_params_are_400(self, api_client, query):
        body = assert_error(api_client.get(f"{LIST_URL}?{query}"), 400)

        assert "details" in body


class TestCreate:
    def test_staff_can_create_product(self, staff_client, product_payload):
        response = staff_client.post(LIST_URL, product_payload)

        assert response.status_code == 201
        body = response.json()
        assert body["category_id"] == product_payload["category_id"]
        product = Product.objects.get(pk=body["id"])
        assert product.name == "Лежак"
        assert str(product.price) == "799.50"
        assert product.stock == 3

    def test_optional_fields_have_defaults(self, staff_client, category, brand):
        payload = {
            "name": "Мінімальний",
            "price": 10,
            "animal_type": "fish",
            "category_id": category.pk,
            "brand_id": brand.pk,
        }

        response = staff_client.post(LIST_URL, payload)

        assert response.status_code == 201
        assert response.json()["stock"] == 0
        assert response.json()["description"] == ""

    def test_anonymous_gets_401(self, api_client, product_payload):
        response = api_client.post(LIST_URL, product_payload)

        body = assert_error(response, 401)
        assert "Authorization: Bearer" in body["error"]
        assert "Bearer" in response["WWW-Authenticate"]
        assert Product.objects.count() == 0

    def test_regular_user_gets_403(self, user_client, product_payload):
        body = assert_error(user_client.post(LIST_URL, product_payload), 403)

        assert body["error"] == "Змінювати каталог можуть лише адміністратори."
        assert Product.objects.count() == 0

    def test_expired_token_gets_401(self, staff_user, product_payload):
        token = AccessToken.for_user(staff_user)
        token.set_exp(lifetime=-timedelta(seconds=1))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        assert_error(client.post(LIST_URL, product_payload), 401)
        assert Product.objects.count() == 0

    def test_empty_body_reports_every_required_field(self, staff_client):
        body = assert_error(staff_client.post(LIST_URL, {}), 400)

        assert set(body["details"]) == {
            "name",
            "price",
            "animal_type",
            "category_id",
            "brand_id",
        }

    @pytest.mark.parametrize(
        ("overrides", "bad_field"),
        [
            ({"name": ""}, "name"),
            ({"price": -5}, "price"),
            ({"price": 0}, "price"),
            ({"price": "abc"}, "price"),
            ({"stock": -1}, "stock"),
            ({"animal_type": "dragon"}, "animal_type"),
            ({"category_id": 999}, "category_id"),
            ({"brand_id": 999}, "brand_id"),
        ],
    )
    def test_invalid_data_is_400(
        self, staff_client, product_payload, overrides, bad_field
    ):
        payload = {**product_payload, **overrides}

        body = assert_error(staff_client.post(LIST_URL, payload), 400)

        assert bad_field in body["details"]
        assert Product.objects.count() == 0

    def test_nonexistent_category_has_readable_message(
        self, staff_client, product_payload
    ):
        payload = {**product_payload, "category_id": 999}

        body = assert_error(staff_client.post(LIST_URL, payload), 400)

        assert body["details"]["category_id"] == ["Категорії з id=999 не існує."]

    def test_broken_json_is_400(self, staff_client):
        response = staff_client.post(
            LIST_URL, "{oops", content_type="application/json"
        )

        body = assert_error(response, 400)
        assert body["error"] == "Некоректний JSON у тілі запиту."


class TestUpdate:
    def test_put_replaces_product(self, staff_client, product, product_payload):
        payload = {**product_payload, "name": "Нова назва"}

        response = staff_client.put(detail_url(product.pk), payload)

        assert response.status_code == 200
        product.refresh_from_db()
        assert product.name == "Нова назва"
        assert product.animal_type == "dog"

    def test_put_without_required_field_is_400(
        self, staff_client, product, product_payload
    ):
        payload = {k: v for k, v in product_payload.items() if k != "name"}

        body = assert_error(staff_client.put(detail_url(product.pk), payload), 400)

        assert "name" in body["details"]
        product.refresh_from_db()
        assert product.name == "Корм для котів"

    def test_patch_changes_only_given_fields(self, staff_client, product):
        response = staff_client.patch(detail_url(product.pk), {"stock": 10})

        assert response.status_code == 200
        assert response.json()["stock"] == 10
        product.refresh_from_db()
        assert product.stock == 10
        assert product.name == "Корм для котів"

    def test_patch_invalid_data_is_400(self, staff_client, product):
        body = assert_error(
            staff_client.patch(detail_url(product.pk), {"price": -1}), 400
        )

        assert "price" in body["details"]

    @pytest.mark.parametrize("method", ["put", "patch"])
    def test_updating_missing_product_is_404(
        self, staff_client, product_payload, method
    ):
        send = getattr(staff_client, method)

        assert_error(send(detail_url(999), product_payload), 404)


class TestDelete:
    def test_staff_can_delete_product(self, staff_client, product):
        response = staff_client.delete(detail_url(product.pk))

        assert response.status_code == 204
        assert not Product.objects.filter(pk=product.pk).exists()
        assert_error(staff_client.get(detail_url(product.pk)), 404)

    def test_deleting_missing_product_is_404(self, staff_client):
        assert_error(staff_client.delete(detail_url(999)), 404)

    def test_delete_on_list_endpoint_is_405(self, staff_client):
        assert_error(staff_client.delete(LIST_URL), 405)


WRITE_ACTIONS = [
    ("post", LIST_URL, {"name": "Нова"}),
    ("put", "/api/products/{pk}", {"name": "Нова"}),
    ("patch", "/api/products/{pk}", {"stock": 99}),
    ("delete", "/api/products/{pk}", None),
]


@pytest.mark.parametrize(("method", "url", "body"), WRITE_ACTIONS)
class TestWriteAccess:

    def test_anonymous_gets_401(self, api_client, product, method, url, body):
        response = getattr(api_client, method)(url.format(pk=product.pk), body)

        assert_error(response, 401)
        self.assert_product_untouched(product)

    def test_regular_user_gets_403(self, user_client, product, method, url, body):
        response = getattr(user_client, method)(url.format(pk=product.pk), body)

        assert_error(response, 403)
        self.assert_product_untouched(product)

    @staticmethod
    def assert_product_untouched(product):
        assert Product.objects.count() == 1
        product.refresh_from_db()
        assert product.name == "Корм для котів"
        assert product.stock == 5
