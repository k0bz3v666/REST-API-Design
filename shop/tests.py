from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken

from .models import Brand, Category, Product


class ApiTestCase(TestCase):
    def setUp(self):
        # Запис у каталог доступний лише адміністратору, тому за замовчуванням
        # усі запити тестового клієнта йдуть з access токеном адміністратора.
        self.admin = get_user_model().objects.create_user(
            username="admin", password="pass-12345", is_staff=True
        )
        self.client.defaults["HTTP_AUTHORIZATION"] = (
            f"Bearer {AccessToken.for_user(self.admin)}"
        )
        self.category = Category.objects.create(name="Корм")
        self.brand = Brand.objects.create(name="Royal Canin", country="Франція")

    def make_product(self, **overrides):
        data = {
            "name": "Корм для котів",
            "price": "250.00",
            "animal_type": "cat",
            "stock": 5,
            "category": self.category,
            "brand": self.brand,
        }
        data.update(overrides)
        return Product.objects.create(**data)

    def assert_error(self, response, status_code):
        self.assertEqual(response.status_code, status_code)
        self.assertIn("error", response.json())
        return response.json()


class CategoryTests(ApiTestCase):
    def test_crud(self):
        r = self.client.post(
            "/api/categories", {"name": "Іграшки"}, content_type="application/json"
        )
        self.assertEqual(r.status_code, 201)
        pk = r.json()["id"]

        self.assertEqual(
            self.client.get(f"/api/categories/{pk}").json()["name"], "Іграшки"
        )
        self.assertEqual(len(self.client.get("/api/categories").json()), 2)

        r = self.client.patch(
            f"/api/categories/{pk}", {"name": "Ласощі"}, content_type="application/json"
        )
        self.assertEqual(r.json()["name"], "Ласощі")
        r = self.client.put(
            f"/api/categories/{pk}", {"name": "Лежаки"}, content_type="application/json"
        )
        self.assertEqual(r.json()["name"], "Лежаки")

        self.assertEqual(self.client.delete(f"/api/categories/{pk}").status_code, 204)
        self.assert_error(self.client.get(f"/api/categories/{pk}"), 404)

    def test_validation(self):
        body = self.assert_error(
            self.client.post("/api/categories", {}, content_type="application/json"),
            400,
        )
        self.assertIn("name", body["details"])
        self.assert_error(
            self.client.post(
                "/api/categories", {"name": "Корм"}, content_type="application/json"
            ),
            400,
        )

    def test_put_requires_all_fields(self):
        self.assert_error(
            self.client.put(
                f"/api/categories/{self.category.pk}",
                {},
                content_type="application/json",
            ),
            400,
        )

    def test_delete_with_products_is_409(self):
        self.make_product()
        body = self.assert_error(
            self.client.delete(f"/api/categories/{self.category.pk}"), 409
        )
        self.assertIn("1", body["error"])
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_products_of_category(self):
        self.make_product()
        r = self.client.get(f"/api/categories/{self.category.pk}/products")
        self.assertEqual(len(r.json()), 1)
        self.assert_error(self.client.get("/api/categories/999/products"), 404)


class BrandTests(ApiTestCase):
    def test_crud(self):
        r = self.client.post(
            "/api/brands",
            {"name": "Purina", "country": "США"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        pk = r.json()["id"]
        self.assertEqual(self.client.get(f"/api/brands/{pk}").json()["country"], "США")
        r = self.client.patch(
            f"/api/brands/{pk}",
            {"description": "Корми"},
            content_type="application/json",
        )
        self.assertEqual(r.json()["description"], "Корми")
        self.assertEqual(self.client.delete(f"/api/brands/{pk}").status_code, 204)
        self.assert_error(self.client.get(f"/api/brands/{pk}"), 404)

    def test_list_has_id_and_name_only(self):
        self.assertEqual(
            self.client.get("/api/brands").json(),
            [{"id": self.brand.pk, "name": "Royal Canin"}],
        )

    def test_delete_with_products_is_409(self):
        self.make_product()
        self.assert_error(self.client.delete(f"/api/brands/{self.brand.pk}"), 409)

    def test_validation(self):
        self.assert_error(
            self.client.post("/api/brands", {}, content_type="application/json"), 400
        )


class ProductTests(ApiTestCase):
    payload = {
        "name": "Лежак",
        "description": "М'який",
        "price": 799.5,
        "animal_type": "dog",
        "weight": "2 кг",
        "stock": 3,
    }

    def payload_with_refs(self, **overrides):
        data = dict(self.payload, category_id=self.category.pk, brand_id=self.brand.pk)
        data.update(overrides)
        return data

    def test_crud(self):
        r = self.client.post(
            "/api/products", self.payload_with_refs(), content_type="application/json"
        )
        self.assertEqual(r.status_code, 201)
        pk = r.json()["id"]
        self.assertEqual(r.json()["category_id"], self.category.pk)

        detail = self.client.get(f"/api/products/{pk}").json()
        self.assertEqual(detail["price"], 799.5)
        self.assertEqual(detail["stock"], 3)

        r = self.client.patch(
            f"/api/products/{pk}", {"stock": 10}, content_type="application/json"
        )
        self.assertEqual(r.json()["stock"], 10)
        self.assertEqual(self.client.delete(f"/api/products/{pk}").status_code, 204)
        self.assert_error(self.client.get(f"/api/products/{pk}"), 404)

    def test_validation(self):
        bad_payloads = [
            {},
            self.payload_with_refs(price=-5),
            self.payload_with_refs(price=0),
            self.payload_with_refs(stock=-1),
            self.payload_with_refs(animal_type="dragon"),
            self.payload_with_refs(category_id=999),
            self.payload_with_refs(brand_id=999),
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                body = self.assert_error(
                    self.client.post(
                        "/api/products", payload, content_type="application/json"
                    ),
                    400,
                )
                self.assertIn("details", body)

    def test_filters_and_sorting(self):
        other_cat = Category.objects.create(name="Іграшки")
        self.make_product(name="Дешевий", price="100")
        self.make_product(name="Дорогий", price="900", animal_type="dog")
        self.make_product(name="М'ячик", price="50", category=other_cat)

        def names(query):
            r = self.client.get(f"/api/products?{query}")
            self.assertEqual(r.status_code, 200)
            return [p["name"] for p in r.json()]

        self.assertEqual(len(names("")), 3)
        self.assertEqual(names("animal_type=dog"), ["Дорогий"])
        self.assertEqual(names(f"category={other_cat.pk}"), ["М'ячик"])
        self.assertEqual(
            names(f"brand={self.brand.pk}&max_price=100&sort=price_asc"),
            ["М'ячик", "Дешевий"],
        )
        self.assertEqual(names("min_price=100&sort=price_desc"), ["Дорогий", "Дешевий"])
        self.assertEqual(names("search=дорогий"), ["Дорогий"])
        self.assertEqual(names("search=royal"), ["Дешевий", "Дорогий", "М'ячик"])

    def test_invalid_filters_are_400(self):
        for query in [
            "sort=popular",
            "animal_type=dragon",
            "min_price=abc",
            "category=x",
            "min_price=10&max_price=5",
        ]:
            with self.subTest(query=query):
                self.assert_error(self.client.get(f"/api/products?{query}"), 400)


class GeneralErrorsTests(ApiTestCase):
    def test_unknown_endpoint_is_404_json(self):
        self.assert_error(self.client.get("/api/nope"), 404)

    def test_method_not_allowed_is_405_json(self):
        self.assert_error(self.client.delete("/api/categories"), 405)

    def test_broken_json_is_400(self):
        self.assert_error(
            self.client.post(
                "/api/categories", "{oops", content_type="application/json"
            ),
            400,
        )

    def test_cors_headers(self):
        r = self.client.get(
            "/api/categories", headers={"Origin": "http://localhost:3000"}
        )
        self.assertEqual(r["Access-Control-Allow-Origin"], "http://localhost:3000")
        r = self.client.get(
            "/api/categories", headers={"Origin": "http://evil.example"}
        )
        self.assertNotIn("Access-Control-Allow-Origin", r)


class PermissionTests(ApiTestCase):
    write_requests = [
        ("post", "/api/categories", {"name": "Нова"}),
        ("put", "/api/categories/{category}", {"name": "Нова"}),
        ("patch", "/api/categories/{category}", {"name": "Нова"}),
        ("delete", "/api/categories/{category}", None),
        ("post", "/api/brands", {"name": "Нова"}),
        ("patch", "/api/brands/{brand}", {"name": "Нова"}),
        ("delete", "/api/brands/{brand}", None),
        ("post", "/api/products", {"name": "Нова"}),
        ("patch", "/api/products/1", {"stock": 1}),
        ("delete", "/api/products/1", None),
    ]

    def send_all(self):
        for method, url, body in self.write_requests:
            url = url.format(category=self.category.pk, brand=self.brand.pk)
            send = getattr(self.client, method)
            if body:
                response = send(url, body, content_type="application/json")
            else:
                response = send(url)
            yield method, url, response

    def test_anonymous_can_read(self):
        del self.client.defaults["HTTP_AUTHORIZATION"]
        product = self.make_product()
        for url in [
            "/api/categories",
            f"/api/categories/{self.category.pk}",
            "/api/brands",
            f"/api/brands/{self.brand.pk}",
            "/api/products",
            f"/api/products/{product.pk}",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_anonymous_cannot_write_401(self):
        del self.client.defaults["HTTP_AUTHORIZATION"]
        for method, url, response in self.send_all():
            with self.subTest(method=method, url=url):
                self.assert_error(response, 401)
        self.assertEqual(Category.objects.count(), 1)

    def test_invalid_token_is_401(self):
        self.client.defaults["HTTP_AUTHORIZATION"] = "Bearer not-a-token"
        self.assert_error(
            self.client.post(
                "/api/categories", {"name": "Нова"}, content_type="application/json"
            ),
            401,
        )

    def test_regular_user_cannot_write_403(self):
        user = get_user_model().objects.create_user(
            username="user", password="pass-12345"
        )
        self.client.defaults["HTTP_AUTHORIZATION"] = (
            f"Bearer {AccessToken.for_user(user)}"
        )
        for method, url, response in self.send_all():
            with self.subTest(method=method, url=url):
                self.assert_error(response, 403)
        self.assertEqual(Category.objects.count(), 1)

    def test_regular_user_can_read(self):
        user = get_user_model().objects.create_user(
            username="user", password="pass-12345"
        )
        self.client.defaults["HTTP_AUTHORIZATION"] = (
            f"Bearer {AccessToken.for_user(user)}"
        )
        self.assertEqual(self.client.get("/api/products").status_code, 200)
