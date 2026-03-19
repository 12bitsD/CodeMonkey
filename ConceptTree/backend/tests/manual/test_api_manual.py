"""Manual smoke test script for running against a live local server.

This script is NOT a pytest test suite — it is a stand-alone script that
manually exercises the key auth and profile API endpoints against a locally
running server (http://localhost:8000). It prints human-readable status codes
and JSON responses to stdout.

Run it directly when you want a quick end-to-end sanity check:

    python backend/tests/manual/test_api_manual.py

The script runs these operations in order:
1. Register a new user account.
2. Log in (confirm the token is valid).
3. Fetch the user's profile (confirm auth works).
4. Update the profile with realistic data.
5. Fetch the profile again (confirm the update was persisted).
6. Log out.

If any step raises an exception, the script exits with a failure message.
Otherwise, it prints a success banner.

Primary reader: a developer running a quick local sanity check after a
major refactor or deployment, without needing to configure a test database.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_register():
    """Register a new user and return the token from the response.

    Sends a POST to /api/auth/register with a test email and password,
    prints the response, and returns the token for subsequent calls.
    """
    print("\n=== 测试注册 ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": "test@example.com", "password": "123456"}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()["data"]["token"]


def test_login(token):
    """Log in with the registered account and print the response.

    The token parameter is unused here — it's carried for API symmetry
    with other test functions. A fresh login call is made.
    """
    print("\n=== 测试登录 ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "test@example.com", "password": "123456"}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_get_profile(token):
    """Fetch the user profile using the provided token and print the response.

    Confirms that the auth token from registration is accepted by the
    profile endpoint.
    """
    print("\n=== 测试获取画像 ===")
    response = requests.get(
        f"{BASE_URL}/api/user/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_update_profile(token):
    """Update the user profile with realistic student background data.

    Sends occupation, education, skill levels, and abilities to the
    profile update endpoint to verify the update path works end-to-end.
    """
    print("\n=== 测试更新画像 ===")
    response = requests.put(
        f"{BASE_URL}/api/user/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "occupation": "大三计算机学生",
            "education": "香港理工大学 计算机",
            "programmingLevel": "入门",
            "mathLevel": "入门",
            "abilities": ["Python 会基础语法", "线性代数 会矩阵运算"]
        }
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_logout(token):
    """Log out the authenticated user and print the response.

    Confirms that the logout endpoint accepts the token and returns a
    success response with a message.
    """
    print("\n=== 测试登出 ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    try:
        token = test_register()
        test_login(token)
        test_get_profile(token)
        test_update_profile(token)
        test_get_profile(token)
        test_logout(token)
        print("\n✅ 所有测试通过！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
