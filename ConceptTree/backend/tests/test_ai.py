"""AI服务API测试"""
import pytest
import os
from fastapi.testclient import TestClient
from main import app
from database import init_database

# 测试数据库路径
TEST_DB = "test_ai.db"


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """每个测试前重建数据库"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # 设置测试数据库
    import config
    config.DATABASE_PATH = TEST_DB
    
    # 初始化数据库
    init_database()
    
    yield
    
    # 清理
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


@pytest.fixture
def auth_user(client):
    """注册并登录一个测试用户"""
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    # 注册
    response = client.post("/api/auth/register", json={
        "email": email,
        "password": "123456"
    })
    data = response.json()["data"]
    return {
        "token": data["token"],
        "user_id": data["user"]["id"]
    }


class TestParseGoal:
    """测试解析学习目标"""
    
    def test_parse_goal_success(self, client, auth_user):
        """测试成功解析学习目标"""
        response = client.post(
            "/api/ai/parse-goal",
            json={"input": "我想学反向传播，我有Python基础但数学不好"},
            headers={"Authorization": f"Bearer {auth_user['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        
        result = data["data"]
        assert "interpretation" in result
        assert "backgroundSummary" in result
        assert "suggestedNodeCount" in result
        assert "shouldSplit" in result
    
    def test_parse_goal_simple_input(self, client, auth_user):
        """测试简单输入（可能需要拆分）"""
        response = client.post(
            "/api/ai/parse-goal",
            json={"input": "深度学习"},
            headers={"Authorization": f"Bearer {auth_user['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        result = data["data"]
        # 简单输入可能会建议拆分
        assert "shouldSplit" in result
        if result["shouldSplit"]:
            assert "splitSuggestions" in result
            assert len(result["splitSuggestions"]) > 0
    
    def test_parse_goal_with_profile(self, client, auth_user):
        """测试带用户画像的解析"""
        # 先更新用户画像
        client.put(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {auth_user['token']}"},
            json={
                "occupation": "大四计算机学生",
                "programmingLevel": "熟练",
                "mathLevel": "入门",
                "abilities": ["Python 熟练使用pandas和numpy"]
            }
        )
        
        # 解析目标
        response = client.post(
            "/api/ai/parse-goal",
            json={"input": "我想学机器学习"},
            headers={"Authorization": f"Bearer {auth_user['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        result = data["data"]
        # 应该包含从画像中提取的背景信息
        assert "backgroundSummary" in result
    
    def test_parse_goal_unauthorized(self, client):
        """测试未认证时解析目标"""
        response = client.post(
            "/api/ai/parse-goal",
            json={"input": "我想学Python"}
        )
        
        assert response.status_code == 403
    
    def test_parse_goal_auto_update_abilities(self, client, auth_user):
        """测试解析目标时自动更新用户画像中的能力"""
        # 解析包含能力信息的输入
        response = client.post(
            "/api/ai/parse-goal",
            json={"input": "我想学深度学习，我会Python和线性代数"},
            headers={"Authorization": f"Bearer {auth_user['token']}"}
        )
        
        assert response.status_code == 200
        
        # 检查用户画像是否被更新
        profile_response = client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {auth_user['token']}"}
        )
        
        profile = profile_response.json()["data"]
        # abilities应该包含从输入中提取的能力
        assert "abilities" in profile


class TestGenerateGraph:
    """测试生成知识图谱"""
    
    def test_generate_graph_success(self, client, auth_user):
        """测试成功生成图谱"""
        response = client.post(
            "/api/ai/generate-graph",
            json={
                "input": "我想学反向传播",
                "interpretation": "理解反向传播的数学原理"
            },
            headers={"Authorization": f"Bearer {auth_user['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        
        result = data["data"]
        assert "nodes" in result
        assert "edges" in result
        assert "targetNodeId" in result
        
        # 验证节点结构
        assert len(result["nodes"]) > 0
        node = result["nodes"][0]
        assert "id" in node
        assert "name" in node
        assert "status" in node
        assert "x" in node
        assert "y" in node
        assert "why" in node
        assert "what" in node
        assert "mastery" in node
        assert "prompt" in node
        assert "resources" in node
        assert "isTarget" in node
        assert "domain" in node
        
        # 验证边结构
        if len(result["edges"]) > 0:
            edge = result["edges"][0]
            assert "from" in edge
            assert "to" in edge
    
    def test_generate_graph_with_mastered_knowledge(self, client, auth_user):
        """测试带已掌握知识的图谱生成"""
        # 先更新用户画像的已掌握知识
        client.put(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {auth_user['token']}"},
            json={"abilities": ["矩阵乘法", "Python基础"]}
        )
        
        response = client.post(
            "/api/ai/generate-graph",
            json={
                "input": "我想学神经网络",
                "interpretation": "理解神经网络的基本原理"
            },
            headers={"Authorization": f"Bearer {auth_user['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        result = data["data"]
        # 应该生成合理的节点数量
        assert len(result["nodes"]) > 0
    
    def test_generate_graph_unauthorized(self, client):
        """测试未认证时生成图谱"""
        response = client.post(
            "/api/ai/generate-graph",
            json={
                "input": "我想学Python",
                "interpretation": "学习Python编程"
            }
        )
        
        assert response.status_code == 403
    
    def test_generate_graph_empty_input(self, client, auth_user):
        """测试空输入"""
        response = client.post(
            "/api/ai/generate-graph",
            json={
                "input": "",
                "interpretation": ""
            },
            headers={"Authorization": f"Bearer {auth_user['token']}"}
        )
        
        # 可能会返回错误或空结果
        assert response.status_code in [200, 422, 500]
    
    def test_generate_graph_node_structure(self, client, auth_user):
        """测试生成的节点结构符合spec要求"""
        response = client.post(
            "/api/ai/generate-graph",
            json={
                "input": "我想学线性代数",
                "interpretation": "掌握线性代数基础"
            },
            headers={"Authorization": f"Bearer {auth_user['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        result = data["data"]
        
        # 检查至少有一个目标节点
        target_nodes = [n for n in result["nodes"] if n.get("isTarget")]
        assert len(target_nodes) > 0
        
        # 检查节点字段类型
        for node in result["nodes"]:
            assert isinstance(node["id"], str)
            assert isinstance(node["name"], str)
            assert isinstance(node["status"], str)
            assert isinstance(node["x"], (int, float))
            assert isinstance(node["y"], (int, float))
            assert isinstance(node["why"], str)
            assert isinstance(node["what"], list)
            assert isinstance(node["mastery"], list)
            assert isinstance(node["prompt"], str)
            assert isinstance(node["resources"], list)
            assert isinstance(node["domain"], str)
            assert isinstance(node["isTarget"], bool)
