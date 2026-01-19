"""认证接口测试"""
import pytest
import os
import sqlite3
from fastapi.testclient import TestClient
from main import app

TEST_DB = "test_auth.db"


@pytest.fixture(autouse=True)
def setup_test_db():
    """每个测试前重建数据库"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # 临时修改数据库路径
    import database
    original_path = database.DATABASE_PATH
    database.DATABASE_PATH = TEST_DB
    
    # 初始化测试数据库
    from database import init_database
    init_database(run_seed=False)
    
    yield
    
    # 恢复原始数据库路径
    database.DATABASE_PATH = original_path
    
    # 清理测试数据库
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


client = TestClient(app)


def test_register_success():
    """测试注册成功"""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "123456"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "user" in data["data"]
    assert "token" in data["data"]
    assert data["data"]["user"]["email"] == "test@example.com"


def test_register_invalid_email():
    """测试邮箱格式错误"""
    response = client.post(
        "/api/auth/register",
        json={"email": "invalid-email", "password": "123456"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_EMAIL"


def test_register_weak_password():
    """测试密码太短"""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "123"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "WEAK_PASSWORD"


def test_register_duplicate_email():
    """测试重复邮箱"""
    # 先注册一次
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "123456"}
    )
    
    # 再次注册相同邮箱
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "654321"}
    )
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "EMAIL_EXISTS"


def test_login_success():
    """测试登录成功"""
    # 先注册
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "123456"}
    )
    
    # 登录
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "123456"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "token" in data["data"]
    assert data["data"]["expiresIn"] == 604800


def test_login_wrong_password():
    """测试密码错误"""
    # 先注册
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "123456"}
    )
    
    # 用错误密码登录
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrong"}
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_user_not_exist():
    """测试用户不存在"""
    response = client.post(
        "/api/auth/login",
        json={"email": "notexist@example.com", "password": "123456"}
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_logout_success():
    """测试登出成功"""
    # 先注册并获取token
    register_resp = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "123456"}
    )
    token = register_resp.json()["data"]["token"]
    
    # 登出
    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "已登出"


def test_logout_without_token():
    """测试无token登出"""
    response = client.post("/api/auth/logout")
    assert response.status_code == 403


def test_register_creates_profile():
    """测试注册时自动创建画像"""
    # 注册用户
    register_resp = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "123456"}
    )
    user_id = register_resp.json()["data"]["user"]["id"]
    
    # 检查数据库中是否创建了画像
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    profile = cursor.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    
    assert profile is not None
    assert profile["programming_level"] == "入门"
    assert profile["math_level"] == "入门"
    
    conn.close()
