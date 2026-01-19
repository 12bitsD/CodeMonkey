"""手动测试API接口"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_register():
    """测试注册"""
    print("\n=== 测试注册 ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": "test@example.com", "password": "123456"}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()["data"]["token"]


def test_login(token):
    """测试登录"""
    print("\n=== 测试登录 ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "test@example.com", "password": "123456"}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_get_profile(token):
    """测试获取画像"""
    print("\n=== 测试获取画像 ===")
    response = requests.get(
        f"{BASE_URL}/api/user/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_update_profile(token):
    """测试更新画像"""
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
    """测试登出"""
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
