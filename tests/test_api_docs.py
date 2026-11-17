import json

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def schema(api_client):
    response = api_client.get("/api/schema", {"format": "json"})
    assert response.status_code == 200
    return json.loads(response.content)


@pytest.mark.parametrize("url", ["/api/docs", "/api/redoc"])
def test_documentation_pages_are_public(api_client, url):
    response = api_client.get(url)

    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]


def test_schema_is_openapi_3(schema):
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "Ly-Jess API"


def test_schema_describes_product_endpoints_and_methods(schema):
    paths = schema["paths"]
    detail_paths = [p for p in paths if p.startswith("/api/products/{")]

    assert {"get", "post"} <= set(paths["/api/products"])
    assert len(detail_paths) == 1
    assert {"get", "put", "patch", "delete"} <= set(paths[detail_paths[0]])


def test_schema_documents_filters_of_product_list(schema):
    parameters = schema["paths"]["/api/products"]["get"]["parameters"]

    assert {
        "search",
        "animal_type",
        "category",
        "brand",
        "min_price",
        "max_price",
        "sort",
    } <= {p["name"] for p in parameters}


def test_schema_documents_error_codes_of_protected_actions(schema):
    detail = next(
        item for path, item in schema["paths"].items()
        if path.startswith("/api/products/{")
    )

    assert {"204", "401", "403", "404"} <= set(detail["delete"]["responses"])
    assert {"201", "400", "401", "403"} <= set(
        schema["paths"]["/api/products"]["post"]["responses"]
    )


def test_schema_declares_bearer_jwt_security(schema):
    scheme = schema["components"]["securitySchemes"]["jwtAuth"]

    assert scheme["type"] == "http"
    assert scheme["scheme"] == "bearer"


def test_schema_contains_only_real_api_endpoints(schema):
    paths = schema["paths"]

    assert all(path.startswith("/api/") for path in paths)
    assert not any(".*" in path for path in paths)
    assert {
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/refresh",
        "/api/auth/me",
    } <= set(paths)
