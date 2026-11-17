import pytest

from shop.models import Brand, Category

pytestmark = pytest.mark.django_db


def error_of(response, status_code):
    assert response.status_code == status_code, response.content
    return response.json()


class TestCategories:
    def test_staff_crud(self, staff_client):
        created = staff_client.post("/api/categories", {"name": "Іграшки"})
        assert created.status_code == 201
        pk = created.json()["id"]

        assert staff_client.patch(f"/api/categories/{pk}", {"name": "Ласощі"}).json()[
            "name"
        ] == "Ласощі"
        assert staff_client.delete(f"/api/categories/{pk}").status_code == 204
        assert staff_client.get(f"/api/categories/{pk}").status_code == 404

    def test_name_must_be_unique(self, staff_client, category):
        body = error_of(staff_client.post("/api/categories", {"name": "Корм"}), 400)

        assert body["details"]["name"] == ["Категорія з такою назвою вже існує."]

    def test_delete_category_with_products_is_409(
        self, staff_client, category, product
    ):
        body = error_of(staff_client.delete(f"/api/categories/{category.pk}"), 409)

        assert "є товари: 1" in body["error"]
        assert Category.objects.filter(pk=category.pk).exists()

    def test_delete_missing_category_is_404(self, staff_client):
        error_of(staff_client.delete("/api/categories/999"), 404)

    def test_regular_user_cannot_create(self, user_client):
        error_of(user_client.post("/api/categories", {"name": "Нова"}), 403)

    def test_anonymous_cannot_create(self, api_client):
        error_of(api_client.post("/api/categories", {"name": "Нова"}), 401)

    def test_products_of_category(self, api_client, category, product):
        response = api_client.get(f"/api/categories/{category.pk}/products")

        assert [p["id"] for p in response.json()] == [product.pk]
        error_of(api_client.get("/api/categories/999/products"), 404)


class TestBrands:
    def test_staff_crud(self, staff_client):
        created = staff_client.post(
            "/api/brands", {"name": "Purina", "country": "США"}
        )
        assert created.status_code == 201
        pk = created.json()["id"]

        assert staff_client.get(f"/api/brands/{pk}").json()["country"] == "США"
        assert staff_client.delete(f"/api/brands/{pk}").status_code == 204

    def test_list_has_only_id_and_name(self, api_client, brand):
        assert api_client.get("/api/brands").json() == [
            {"id": brand.pk, "name": "Royal Canin"}
        ]

    def test_delete_brand_with_products_is_409(self, staff_client, brand, product):
        error_of(staff_client.delete(f"/api/brands/{brand.pk}"), 409)

        assert Brand.objects.filter(pk=brand.pk).exists()

    def test_regular_user_cannot_delete(self, user_client, brand):
        error_of(user_client.delete(f"/api/brands/{brand.pk}"), 403)
        assert Brand.objects.filter(pk=brand.pk).exists()
