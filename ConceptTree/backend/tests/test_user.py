"""User profile API validates auth protection and data persistence.

This module covers two key scenarios:
1. The profile endpoint is protected — unauthenticated requests are rejected.
2. A user can update their profile fields (occupation, education, skill levels,
   abilities) and immediately read back the saved values.

Primary reader: a developer verifying that user-profile changes are persisted
correctly or debugging a 401 on the profile endpoint.
"""


def test_get_profile_requires_auth(client):
    """Fetching the profile without a token is rejected with HTTP 401.

    The profile endpoint must never return data to an unauthenticated caller.
    Expected: HTTP 401.
    """
    resp = client.get("/api/user/profile")
    assert resp.status_code == 401


def test_update_profile_success(client, auth_headers_a):
    """A user can update profile fields and read back the updated values immediately.

    Sends a PUT with occupation, education, programming/math levels, and an
    abilities list, then confirms via a subsequent GET that the occupation
    field was persisted correctly.
    Expected: PUT returns HTTP 200 with success=True; GET returns the saved
    occupation value.
    """
    update = {
        "occupation": "学生",
        "education": "本科",
        "programmingLevel": "入门",
        "mathLevel": "入门",
        "abilities": ["Python"],
    }
    resp = client.put("/api/user/profile", json=update, headers=auth_headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    get_resp = client.get("/api/user/profile", headers=auth_headers_a)
    assert get_resp.status_code == 200
    profile = get_resp.json()["data"]
    assert profile["occupation"] == "学生"
