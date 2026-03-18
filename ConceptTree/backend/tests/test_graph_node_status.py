import json

import pytest


def test_update_node_status_requires_auth(client):
    resp = client.put(
        "/api/plans/p_any/nodes/n_any/status",
        json={"status": "learned"},
    )
    assert resp.status_code == 401


def test_update_node_status_to_learned(client, auth_headers_a):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "status_n1",
                "name": "节点A",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "status_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/status_n1/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["nodeId"] == "status_n1"
    assert body["data"]["status"] == "learned"
    assert "plan" in body["data"]
    assert body["data"]["plan"]["progress"] == 1


def test_update_node_status_to_skipped(client, auth_headers_a):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "skip_n1",
                "name": "节点B",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": False,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "skip_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/skip_n1/status",
        json={"status": "skipped"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "skipped"


def test_update_node_status_invalid_status(client, auth_headers_a):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "inv_n1",
                "name": "节点",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "inv_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/inv_n1/status",
        json={"status": "invalid_status"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 400


def test_update_node_status_plan_not_found(client, auth_headers_a):
    resp = client.put(
        "/api/plans/nonexistent/nodes/n1/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_update_node_status_node_not_found(client, auth_headers_a):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "n_exists",
                "name": "存在的节点",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "n_exists",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/nonexistent_node/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404


def test_update_node_status_forbidden_other_user(client, auth_headers_a, auth_headers_b):
    plan_data = {
        "title": "用户A的计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "other_n1",
                "name": "节点",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "other_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/other_n1/status",
        json={"status": "learned"},
        headers=auth_headers_b,
    )
    assert resp.status_code == 403


def test_update_node_status_creates_learning_session(client, auth_headers_a):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "session_n1",
                "name": "学习会话节点",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            }
        ],
        "edges": [],
        "targetNodeId": "session_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/session_n1/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200


def test_update_node_status_learned_updates_mastered_knowledge(client, auth_headers_a):
    plan_data = {
        "title": "测试计划",
        "originalInput": "input",
        "nodes": [
            {
                "id": "mastery_n1",
                "name": "矩阵乘法",
                "status": "unlearned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "数学",
            }
        ],
        "edges": [],
        "targetNodeId": "mastery_n1",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/mastery_n1/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200


def test_update_node_status_progress_calculation(client, auth_headers_a):
    plan_data = {
        "title": "进度测试",
        "originalInput": "input",
        "nodes": [
            {
                "id": "prog_n1",
                "name": "已学习",
                "status": "learned",
                "x": 0,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": False,
                "domain": "编程",
            },
            {
                "id": "prog_n2",
                "name": "未学习",
                "status": "unlearned",
                "x": 10,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": False,
                "domain": "编程",
            },
            {
                "id": "prog_n3",
                "name": "已跳过",
                "status": "skipped",
                "x": 20,
                "y": 0,
                "why": "",
                "what": [],
                "mastery": [],
                "prompt": "",
                "resources": [],
                "isTarget": True,
                "domain": "编程",
            },
        ],
        "edges": [],
        "targetNodeId": "prog_n3",
    }
    create = client.post("/api/plans", json=plan_data, headers=auth_headers_a)
    plan_id = create.json()["data"]["id"]

    resp = client.put(
        f"/api/plans/{plan_id}/nodes/prog_n2/status",
        json={"status": "learned"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["plan"]["progress"] == 2
    assert body["data"]["plan"]["total"] == 2
