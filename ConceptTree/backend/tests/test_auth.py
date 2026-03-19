"""Authentication API covers the full register → login → logout lifecycle.

This module validates three key scenarios:
1. A new user can successfully register, log in, and log out.
2. Invalid inputs (bad email format, short password, duplicate email) are
   rejected with the correct HTTP status codes and error codes.
3. Protected endpoints (logout) refuse requests that carry no token or an
   invalid token.

Primary reader: a developer debugging an auth failure or reviewing the
security contract of the /api/auth/* endpoints.
"""


def test_register_login_logout_success(client):
    """A new user can register, receive a token, and then log out with it.

    Exercises the full happy-path auth lifecycle in a single test to confirm
    that the token issued at login is accepted by the logout endpoint.
    Expected: all three calls return HTTP 200 with success=True; the logout
    response body contains a human-readable message.
    """
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
    """Registration rejects strings that are not valid email addresses.

    A string such as 'not-an-email' (no '@') must be refused immediately
    rather than stored and discovered later.
    Expected: HTTP 400, success=False, error code INVALID_EMAIL.
    """
    resp = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_EMAIL"


def test_register_weak_password_too_short(client):
    """Registration rejects passwords that are too short to be secure.

    A 5-character password ('12345') is below the minimum length threshold.
    Expected: HTTP 400, success=False, error code WEAK_PASSWORD.
    """
    resp = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "12345"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "WEAK_PASSWORD"


def test_register_email_already_exists(client):
    """Registration rejects a second account using an email that is already taken.

    The first registration succeeds; the second attempt with the same email
    (even with a different password) must be blocked.
    Expected: HTTP 409, success=False, error code EMAIL_EXISTS.
    """
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
    """Login fails when no account exists for the given email.

    Attempting to log in with a never-registered email should not reveal
    whether the account exists or not — both 'not found' and 'wrong password'
    use the same error code to prevent user enumeration.
    Expected: HTTP 401, success=False, error code INVALID_CREDENTIALS.
    """
    resp = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_wrong_password(client):
    """Login fails when the password does not match the registered one.

    The same INVALID_CREDENTIALS error code is used for both 'user not found'
    and 'wrong password', preventing an attacker from confirming valid emails.
    Expected: HTTP 401, success=False, error code INVALID_CREDENTIALS.
    """
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
    """Logout requires a valid JWT; calling it with no Authorization header is rejected.

    Expected: HTTP 401 (unauthenticated).
    """
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 401


def test_logout_invalid_token(client):
    """Logout rejects a malformed or tampered JWT token.

    Sending an arbitrary string as the Bearer token must not succeed.
    Expected: HTTP 401 (unauthenticated).
    """
    resp = client.post(
        "/api/auth/logout",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert resp.status_code == 401
