from http.cookies import SimpleCookie

import pytest


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _AdminDb:
    def __init__(self, row):
        self.row = row

    def execute(self, sql, params=None):
        assert "JOIN user_roles" in sql
        return _Result(self.row)


def _cookie_value(response, name):
    cookies = SimpleCookie()
    cookies.load(response.headers["set-cookie"])
    return cookies[name].value


@pytest.mark.no_db
def test_admin_session_requires_database_role(monkeypatch):
    from main import app
    from database import get_db
    from utils.auth import create_access_token

    app.dependency_overrides[get_db] = lambda: _AdminDb(None)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'u_regular', 'role': 'admin'})}"}
    try:
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.post(
                "/api/admin/auth/session",
                headers=headers,
                json={"password": "password123"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ADMIN_ACCESS_DENIED"


@pytest.mark.no_db
def test_admin_can_elevate_and_access_identity():
    from database import get_db
    from main import app
    from utils.auth import create_access_token
    from utils.password import hash_password

    row = {
        "id": "u_admin",
        "email": "owner@example.com",
        "password_hash": hash_password("password123"),
    }
    app.dependency_overrides[get_db] = lambda: _AdminDb(row)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'u_admin'})}"}
    try:
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            login = client.post(
                "/api/admin/auth/session",
                headers=headers,
                json={"password": "password123"},
            )
            admin_cookie = _cookie_value(login, "concept_tree_admin_session")
            identity = client.get(
                "/api/admin/me",
                headers={"Cookie": f"concept_tree_admin_session={admin_cookie}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert login.status_code == 200
    assert "HttpOnly" in login.headers["set-cookie"]
    assert "SameSite=strict" in login.headers["set-cookie"]
    assert identity.status_code == 200
    assert identity.json()["data"]["user"] == {"id": "u_admin", "role": "admin"}


@pytest.mark.no_db
def test_admin_endpoint_rejects_missing_cookie():
    from main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.get("/api/admin/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ADMIN_SESSION_REQUIRED"
