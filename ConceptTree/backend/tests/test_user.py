"""用户画像接口测试"""
import pytest
import os
import sqlite3
import json
from fastapi.testclient import TestClient
from main import app

TEST_DB = "test_user.db"


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


def create_test_user():
    """辅助函数：创建测试用户并返回token"""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "123456"}
    )
    return response.json()["data"]["token"]


def test_get_profile_success():
    """测试获取画像成功"""
    token = create_test_user()
    
    response = client.get(
        "/api/user/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "occupation" in data["data"]
    assert "education" in data["data"]
    assert "programmingLevel" in data["data"]
    assert "mathLevel" in data["data"]
    assert "abilities" in data["data"]
    assert "masteredKnowledge" in data["data"]
    assert data["data"]["programmingLevel"] == "入门"
    assert data["data"]["mathLevel"] == "入门"


def test_get_profile_without_auth():
    """测试未认证获取画像"""
    response = client.get("/api/user/profile")
    assert response.status_code == 403


def test_update_occupation():
    """测试更新职业"""
    token = create_test_user()
    
    response = client.put(
        "/api/user/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"occupation": "大三计算机学生"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["occupation"] == "大三计算机学生"


def test_update_education():
    """测试更新教育背景"""
    token = create_test_user()
    
    response = client.put(
        "/api/user/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"education": "香港理工大学 计算机"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["education"] == "香港理工大学 计算机"


def test_update_programming_level():
    """测试更新编程水平"""
    token = create_test_user()
    
    response = client.put(
        "/api/user/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"programmingLevel": "熟练"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["programmingLevel"] == "熟练"


def test_update_math_level():
    """测试更新数学水平"""
    token = create_test_user()
    
    response = client.put(
        "/api/user/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"mathLevel": "无基础"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["mathLevel"] == "无基础"


def test_update_abilities():
    """测试更新能力标签"""
    token = create_test_user()
    
    abilities = ["Python 基础", "JavaScript React"]
    response = client.put(
        "/api/user/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"abilities": abilities}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["abilities"] == abilities


def test_update_multiple_fields():
    """测试批量更新多个字段"""
    token = create_test_user()
    
    update_data = {
        "occupation": "大四学生",
        "education": "清华大学",
        "programmingLevel": "熟练",
        "mathLevel": "入门",
        "abilities": ["Python", "JavaScript", "C++"]
    }
    
    response = client.put(
        "/api/user/profile",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["occupation"] == "大四学生"
    assert data["data"]["education"] == "清华大学"
    assert data["data"]["programmingLevel"] == "熟练"
    assert data["data"]["mathLevel"] == "入门"
    assert len(data["data"]["abilities"]) == 3


def test_mastered_knowledge_readonly():
    """测试masteredKnowledge字段只读"""
    token = create_test_user()
    
    # 尝试更新masteredKnowledge（应该被忽略）
    response = client.put(
        "/api/user/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "occupation": "学生",
            "masteredKnowledge": ["这个不应该被更新"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["masteredKnowledge"] == []  # 应该保持为空


def test_update_profile_without_auth():
    """测试未认证更新画像"""
    response = client.put(
        "/api/user/profile",
        json={"occupation": "学生"}
    )
    assert response.status_code == 403
