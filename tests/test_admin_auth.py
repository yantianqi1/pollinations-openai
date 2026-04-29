import unittest
from contextlib import contextmanager
from typing import Iterator

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@contextmanager
def admin_key(value: str) -> Iterator[None]:
    original_key = settings.admin_panel_key
    settings.admin_panel_key = value
    try:
        yield
    finally:
        settings.admin_panel_key = original_key


class AdminAuthTest(unittest.TestCase):
    def test_public_root_shows_only_login_panel(self) -> None:
        with admin_key("secret-key"):
            response = TestClient(app).get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("zimage", response.text)
        self.assertNotIn("状态总览", response.text)

    def test_public_static_index_shows_only_login_panel(self) -> None:
        with admin_key("secret-key"):
            response = TestClient(app).get("/static/index.html")

        self.assertEqual(response.status_code, 200)
        self.assertIn("zimage", response.text)
        self.assertNotIn("状态总览", response.text)

    def test_admin_stats_requires_login(self) -> None:
        with admin_key("secret-key"):
            response = TestClient(app).get("/admin/stats")

        self.assertEqual(response.status_code, 401)

    def test_wrong_login_key_is_rejected(self) -> None:
        with admin_key("secret-key"):
            response = TestClient(app).post(
                "/admin/login",
                json={"key": "wrong-key"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("zimage_admin_session", response.cookies)

    def test_login_cookie_unlocks_panel_and_admin_api(self) -> None:
        with admin_key("secret-key"):
            client = TestClient(app)
            login = client.post("/admin/login", json={"key": "secret-key"})
            page = client.get("/")
            stats = client.get("/admin/stats")

        self.assertEqual(login.status_code, 200)
        self.assertIn("zimage_admin_session", login.cookies)
        self.assertEqual(page.status_code, 200)
        self.assertIn("状态总览", page.text)
        self.assertEqual(stats.status_code, 200)
