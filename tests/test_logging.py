import logging

import pytest

pytestmark = pytest.mark.django_db


def records_of(caplog, logger_name):
    return [r for r in caplog.records if r.name == logger_name]


def test_product_creation_is_logged_at_info(
    staff_client, staff_user, product_payload, caplog
):
    caplog.set_level(logging.INFO)

    response = staff_client.post("/api/products", product_payload)

    pk = response.json()["id"]
    messages = [
        r.getMessage()
        for r in records_of(caplog, "shop.views")
        if r.levelno == logging.INFO
    ]
    assert f"Created Product id={pk} (user_id={staff_user.pk})" in messages


def test_forbidden_action_is_logged_as_warning(
    user_client, regular_user, product, caplog
):
    caplog.set_level(logging.INFO)

    user_client.delete(f"/api/products/{product.pk}")

    warnings = [
        r.getMessage()
        for r in records_of(caplog, "shop.errors")
        if r.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    assert "403" in warnings[0]
    assert f"user_id={regular_user.pk}" in warnings[0]


def test_anonymous_attempt_is_logged_as_warning(api_client, product, caplog):
    caplog.set_level(logging.INFO)

    api_client.delete(f"/api/products/{product.pk}")

    warnings = [
        r.getMessage()
        for r in records_of(caplog, "shop.errors")
        if r.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    assert "401" in warnings[0]
    assert "anonymous" in warnings[0]


def test_refused_category_delete_is_logged_as_warning(
    staff_client, category, product, caplog
):
    caplog.set_level(logging.INFO)

    staff_client.delete(f"/api/categories/{category.pk}")

    messages = [
        r.getMessage()
        for r in records_of(caplog, "shop.views")
        if r.levelno == logging.WARNING
    ]
    assert any(f"Category id={category.pk} refused" in m for m in messages)


def test_not_found_is_debug_only(api_client, caplog):
    caplog.set_level(logging.INFO)
    api_client.get("/api/products/999")
    assert records_of(caplog, "shop.errors") == []

    caplog.set_level(logging.DEBUG)
    api_client.get("/api/products/999")
    debug = records_of(caplog, "shop.errors")
    assert len(debug) == 1
    assert debug[0].levelno == logging.DEBUG


def test_login_logs_event_but_not_password_or_tokens(
    api_client, regular_user, password, caplog
):
    caplog.set_level(logging.DEBUG)

    response = api_client.post(
        "/api/auth/login", {"username": "olena", "password": password}
    )

    assert response.status_code == 200
    assert f"User logged in: user_id={regular_user.pk}" in caplog.text
    assert password not in caplog.text
    assert response.json()["access"] not in caplog.text
    assert response.json()["refresh"] not in caplog.text


def test_failed_login_does_not_log_password(
    api_client, regular_user, caplog
):
    caplog.set_level(logging.DEBUG)
    wrong_password = "super-secret-wrong-pass"

    response = api_client.post(
        "/api/auth/login", {"username": "olena", "password": wrong_password}
    )

    assert response.status_code == 401
    assert wrong_password not in caplog.text
    assert any(
        r.levelno == logging.WARNING and "401" in r.getMessage()
        for r in records_of(caplog, "shop.errors")
    )


def test_registration_is_logged_without_credentials(api_client, caplog):
    caplog.set_level(logging.DEBUG)
    payload = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "Str0ng-pass-42",
        "password_confirm": "Str0ng-pass-42",
    }

    response = api_client.post("/api/auth/register", payload)

    assert response.status_code == 201
    assert f"New user registered: user_id={response.json()['id']}" in caplog.text
    assert payload["password"] not in caplog.text


def test_validation_error_logs_field_names_not_values(api_client, caplog):
    caplog.set_level(logging.DEBUG)
    weak = "password123"

    response = api_client.post(
        "/api/auth/register",
        {
            "username": "newuser",
            "email": "new@example.com",
            "password": weak,
            "password_confirm": weak,
        },
    )

    assert response.status_code == 400
    assert "fields=['password']" in caplog.text
    assert weak not in caplog.text
