def test_register_login_logout_success(client):
    email = "new_user@example.com"
    password = "password123"

    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["success"] is True
    token = body["data"]["token"]

    logout = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout.status_code == 200
    body = logout.json()
    assert body["success"] is True
    assert "data" in body
    assert "message" in body["data"]


def test_register_invalid_email_format(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_EMAIL"


def test_register_weak_password_too_short(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "12345"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "WEAK_PASSWORD"


def test_register_email_already_exists(client):
    client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "password123"},
    )
    resp = client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "password456"},
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "EMAIL_EXISTS"


def test_login_user_not_found(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={"email": "wrongpw@example.com", "password": "correctpassword"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "wrongpw@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


def test_logout_without_token(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 401


def test_logout_invalid_token(client):
    resp = client.post(
        "/api/auth/logout",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert resp.status_code == 401
