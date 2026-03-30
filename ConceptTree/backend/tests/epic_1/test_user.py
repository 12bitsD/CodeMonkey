def test_get_profile_requires_auth(client):
    resp = client.get("/api/user/profile")
    assert resp.status_code == 401


def test_update_profile_success(client, auth_headers_a):
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
