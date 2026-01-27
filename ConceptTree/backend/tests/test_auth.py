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
