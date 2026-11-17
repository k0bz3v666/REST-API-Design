from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
REFRESH_URL = "/api/auth/refresh"
ME_URL = "/api/auth/me"


class AuthTestCase(TestCase):
    valid_payload = {
        "username": "olena",
        "first_name": "Олена",
        "last_name": "Коваль",
        "email": "olena@example.com",
        "password": "Str0ng-pass-42",
        "password_confirm": "Str0ng-pass-42",
    }

    def post(self, url, payload):
        return self.client.post(url, payload, content_type="application/json")

    def register(self, **overrides):
        return self.post(REGISTER_URL, dict(self.valid_payload, **overrides))

    def assert_error(self, response, status_code):
        self.assertEqual(response.status_code, status_code)
        self.assertIn("error", response.json())
        return response.json()


class RegisterTests(AuthTestCase):
    def test_success(self):
        r = self.register()
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertEqual(body["username"], "olena")
        self.assertEqual(body["email"], "olena@example.com")
        self.assertNotIn("password", body)
        self.assertNotIn("password_confirm", body)

    def test_password_is_hashed(self):
        self.register()
        user = User.objects.get(username="olena")
        self.assertNotEqual(user.password, self.valid_payload["password"])
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertTrue(user.check_password(self.valid_payload["password"]))

    def test_new_user_is_not_admin(self):
        self.register()
        self.assertFalse(User.objects.get(username="olena").is_staff)

    def test_names_are_optional(self):
        payload = dict(self.valid_payload)
        del payload["first_name"], payload["last_name"]
        r = self.post(REGISTER_URL, payload)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["first_name"], "")

    def test_required_fields(self):
        for field in ["username", "email", "password", "password_confirm"]:
            with self.subTest(field=field):
                payload = dict(self.valid_payload)
                del payload[field]
                body = self.assert_error(self.post(REGISTER_URL, payload), 400)
                self.assertIn(field, body["details"])

    def test_blank_required_fields(self):
        for field in ["username", "email", "password"]:
            with self.subTest(field=field):
                body = self.assert_error(self.register(**{field: ""}), 400)
                self.assertIn(field, body["details"])

    def test_max_length(self):
        for field, limit in [
            ("username", 150),
            ("first_name", 150),
            ("last_name", 150),
        ]:
            with self.subTest(field=field):
                body = self.assert_error(
                    self.register(**{field: "a" * (limit + 1)}), 400
                )
                self.assertIn(field, body["details"])
        body = self.assert_error(self.register(email="a" * 250 + "@example.com"), 400)
        self.assertIn("email", body["details"])

    def test_invalid_email(self):
        for email in ["olena", "olena@", "@example.com", "olena@example"]:
            with self.subTest(email=email):
                body = self.assert_error(self.register(email=email), 400)
                self.assertIn("email", body["details"])

    def test_short_password(self):
        body = self.assert_error(
            self.register(password="Ab1!", password_confirm="Ab1!"), 400
        )
        self.assertIn("password", body["details"])

    def test_weak_passwords(self):
        for password in ["12345678901", "password123", "olena123"]:
            with self.subTest(password=password):
                body = self.assert_error(
                    self.register(password=password, password_confirm=password), 400
                )
                self.assertIn("password", body["details"])

    def test_passwords_must_match(self):
        body = self.assert_error(self.register(password_confirm="Other-pass-42"), 400)
        self.assertIn("password_confirm", body["details"])
        self.assertFalse(User.objects.exists())

    def test_username_and_email_are_unique_ignoring_case(self):
        self.assertEqual(self.register().status_code, 201)
        body = self.assert_error(
            self.register(username="OLENA", email="other@example.com"), 400
        )
        self.assertIn("username", body["details"])
        body = self.assert_error(
            self.register(username="other", email="OLENA@example.com"), 400
        )
        self.assertIn("email", body["details"])

    def test_every_field_error_is_reported_at_once(self):
        body = self.assert_error(self.post(REGISTER_URL, {}), 400)
        self.assertEqual(
            set(body["details"]),
            {"username", "email", "password", "password_confirm"},
        )


class LoginTests(AuthTestCase):
    def setUp(self):
        self.register()

    def login(self, **overrides):
        payload = {"username": "olena", "password": self.valid_payload["password"]}
        return self.post(LOGIN_URL, dict(payload, **overrides))

    def test_success_returns_tokens_and_user(self):
        r = self.login()
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("access", body)
        self.assertIn("refresh", body)
        self.assertEqual(body["user"]["username"], "olena")
        self.assertFalse(body["user"]["is_staff"])

    def test_wrong_password_is_401(self):
        self.assert_error(self.login(password="wrong-pass-1"), 401)

    def test_unknown_user_is_401(self):
        self.assert_error(self.login(username="nobody"), 401)

    def test_missing_fields_is_400(self):
        body = self.assert_error(self.post(LOGIN_URL, {}), 400)
        self.assertIn("username", body["details"])
        self.assertIn("password", body["details"])


class RefreshTests(AuthTestCase):
    def setUp(self):
        self.register()
        self.tokens = self.post(
            LOGIN_URL,
            {"username": "olena", "password": self.valid_payload["password"]},
        ).json()

    def test_refresh_returns_working_access_token(self):
        r = self.post(REFRESH_URL, {"refresh": self.tokens["refresh"]})
        self.assertEqual(r.status_code, 200)
        r = self.client.get(
            ME_URL, headers={"Authorization": f"Bearer {r.json()['access']}"}
        )
        self.assertEqual(r.status_code, 200)

    def test_invalid_refresh_is_401(self):
        self.assert_error(self.post(REFRESH_URL, {"refresh": "garbage"}), 401)

    def test_access_token_cannot_be_used_as_refresh(self):
        self.assert_error(
            self.post(REFRESH_URL, {"refresh": self.tokens["access"]}), 401
        )

    def test_expired_refresh_is_401(self):
        token = RefreshToken.for_user(User.objects.get(username="olena"))
        token.set_exp(lifetime=-timedelta(seconds=1))
        self.assert_error(self.post(REFRESH_URL, {"refresh": str(token)}), 401)

    def test_missing_refresh_is_400(self):
        self.assert_error(self.post(REFRESH_URL, {}), 400)


class MeTests(AuthTestCase):
    def setUp(self):
        self.register()
        self.user = User.objects.get(username="olena")

    def auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_returns_current_user(self):
        r = self.client.get(ME_URL, headers=self.auth(AccessToken.for_user(self.user)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["username"], "olena")
        self.assertNotIn("password", r.json())

    def test_without_token_is_401(self):
        r = self.client.get(ME_URL)
        self.assert_error(r, 401)
        self.assertIn("Bearer", r["WWW-Authenticate"])

    def test_expired_access_token_is_401(self):
        token = AccessToken.for_user(self.user)
        token.set_exp(lifetime=-timedelta(seconds=1))
        self.assert_error(self.client.get(ME_URL, headers=self.auth(token)), 401)

    def test_refresh_token_is_not_accepted_as_access(self):
        token = RefreshToken.for_user(self.user)
        self.assert_error(self.client.get(ME_URL, headers=self.auth(token)), 401)

    def test_inactive_user_is_rejected(self):
        token = AccessToken.for_user(self.user)
        self.user.is_active = False
        self.user.save()
        self.assert_error(self.client.get(ME_URL, headers=self.auth(token)), 401)
