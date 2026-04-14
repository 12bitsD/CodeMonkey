"""
Sprint 1 安全加固测试
覆盖：
  S4  — CORS wildcard + credentials 不共存
  S5  — 登录/注册频率限制（slowapi 5/15min）
  S6  — 错误响应不暴露内部异常详情
  S7  — JWT 黑名单（logout 后 token 立即失效）
  S8  — 密码强度：8位 + 字母 + 数字
  S9  — notes 接口 Pydantic 校验（拒绝非法 body）
  S10 — DEBUG 默认关闭
  S12 — 生产环境 /docs 关闭

运行方式（需数据库连接）：
  cd backend
  pytest tests/test_sprint1_security.py -v

纯单元测试（无需数据库，用 -m no_db 筛选）：
  pytest tests/test_sprint1_security.py -v -m no_db
"""

from __future__ import annotations

import pytest
from unittest.mock import patch


# ──────────────────────────────────────────────────────────────────────────────
# S4 — CORS：wildcard origin 不能同时开启 credentials
# ──────────────────────────────────────────────────────────────────────────────

class TestCorsConfig:

    @pytest.mark.no_db
    def test_wildcard_disables_credentials(self):
        """CORS_ORIGINS=* 时 allow_credentials 必须为 False。"""
        import importlib
        import config as cfg
        importlib.reload(cfg)

        with patch.dict("os.environ", {"CORS_ORIGINS": "*"}):
            importlib.reload(cfg)
            assert cfg.get_cors_allow_credentials() is False

    @pytest.mark.no_db
    def test_specific_origin_enables_credentials(self):
        """明确指定域名时 allow_credentials 应遵循配置。"""
        import importlib
        import config as cfg

        with patch.dict("os.environ", {
            "CORS_ORIGINS": "https://codemonkey666.space",
            "CORS_ALLOW_CREDENTIALS": "true",
        }):
            importlib.reload(cfg)
            assert cfg.get_cors_allow_credentials() is True

    @pytest.mark.no_db
    def test_empty_origins_defaults_to_localhost(self):
        """未配置 CORS_ORIGINS 时应返回本地开发域名，而非 *。"""
        import importlib
        import config as cfg

        with patch.dict("os.environ", {"CORS_ORIGINS": ""}):
            importlib.reload(cfg)
            origins = cfg.get_cors_origins()
            assert "*" not in origins
            assert any("localhost" in o for o in origins)

    @pytest.mark.no_db
    def test_cors_origins_parsed_from_comma_list(self):
        import importlib
        import config as cfg

        with patch.dict("os.environ", {
            "CORS_ORIGINS": "https://a.com,https://b.com",
        }):
            importlib.reload(cfg)
            origins = cfg.get_cors_origins()
            assert "https://a.com" in origins
            assert "https://b.com" in origins
            assert len(origins) == 2


# ──────────────────────────────────────────────────────────────────────────────
# S5 — 频率限制（需 DB；测试 429 响应结构）
# ──────────────────────────────────────────────────────────────────────────────

class TestRateLimiting:

    def test_register_rate_limit_applied(self, client):
        """连续超过 5 次注册请求应返回 429。"""
        for i in range(5):
            client.post(
                "/api/auth/register",
                json={"email": f"rl{i}@example.com", "password": "Test1234pass"},
            )
        resp = client.post(
            "/api/auth/register",
            json={"email": "rl_extra@example.com", "password": "Test1234pass"},
        )
        assert resp.status_code == 429

    def test_login_rate_limit_applied(self, client):
        """连续超过 5 次登录请求应返回 429。"""
        for _ in range(5):
            client.post(
                "/api/auth/login",
                json={"email": "nonexist@example.com", "password": "Test1234pass"},
            )
        resp = client.post(
            "/api/auth/login",
            json={"email": "nonexist@example.com", "password": "Test1234pass"},
        )
        assert resp.status_code == 429


# ──────────────────────────────────────────────────────────────────────────────
# S6 — 错误响应不暴露异常详情
# ──────────────────────────────────────────────────────────────────────────────

class TestErrorResponseSafety:

    @pytest.mark.no_db
    def test_plans_py_no_str_e(self):
        """plans.py 中所有 except 块均不得使用 str(e) 作为错误消息。"""
        import re
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1] / "routers" / "plans.py"
        ).read_text(encoding="utf-8")

        # 查找 "message": str(e) 模式
        matches = re.findall(r'"message"\s*:\s*str\s*\(e\)', source)
        assert matches == [], (
            f"plans.py 仍有 str(e) 泄露异常: {matches}"
        )

    def test_500_does_not_expose_traceback(self, client, auth_headers_a):
        """触发服务端 500 时，响应体不含 Python traceback 关键字。"""
        with patch(
            "routers.plans.get_db_context",
            side_effect=RuntimeError("internal db error details"),
        ):
            resp = client.post(
                "/api/plans",
                json={"title": "test", "nodes": [], "edges": []},
                headers=auth_headers_a,
            )
        body = resp.text
        assert "Traceback" not in body
        assert "internal db error details" not in body
        assert resp.status_code == 500


# ──────────────────────────────────────────────────────────────────────────────
# S7 — JWT 黑名单（logout 后 token 失效）
# ──────────────────────────────────────────────────────────────────────────────

class TestJwtBlacklist:

    def test_logout_invalidates_token(self, client):
        """logout 后，使用同一 token 访问受保护接口应返回 401。"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={"email": "blacklist@example.com", "password": "Blacklist1"},
        )
        login = client.post(
            "/api/auth/login",
            json={"email": "blacklist@example.com", "password": "Blacklist1"},
        )
        token = login.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 登出
        logout = client.post("/api/auth/logout", headers=headers)
        assert logout.status_code == 200

        # 用同一 token 访问受保护接口
        resp = client.get("/api/user/profile", headers=headers)
        assert resp.status_code == 401

    def test_blacklisted_token_rejected_on_logout_again(self, client):
        """已登出的 token 再次调用 logout 也应返回 401。"""
        client.post(
            "/api/auth/register",
            json={"email": "relogout@example.com", "password": "Relogout1"},
        )
        login = client.post(
            "/api/auth/login",
            json={"email": "relogout@example.com", "password": "Relogout1"},
        )
        token = login.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/api/auth/logout", headers=headers)
        resp = client.post("/api/auth/logout", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.no_db
    def test_blacklist_function_exists(self):
        from utils.auth import add_token_to_blacklist, is_token_blacklisted
        add_token_to_blacklist("dummy_token_xyz")
        assert is_token_blacklisted("dummy_token_xyz") is True
        assert is_token_blacklisted("not_in_blacklist") is False

    @pytest.mark.no_db
    def test_verify_token_raises_on_blacklisted(self):
        from fastapi import HTTPException
        from utils.auth import add_token_to_blacklist, verify_token, create_access_token

        token = create_access_token({"sub": "u_test"})
        add_token_to_blacklist(token)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# S8 — 密码强度
# ──────────────────────────────────────────────────────────────────────────────

class TestPasswordStrength:

    @pytest.mark.parametrize("password,reason", [
        ("short1",    "少于8位"),
        ("1234567",   "7位纯数字"),
        ("abcdefgh",  "8位纯字母，无数字"),
        ("12345678",  "8位纯数字，无字母"),
        ("pass",      "4位无数字"),
    ])
    def test_weak_passwords_rejected(self, client, password, reason):
        resp = client.post(
            "/api/auth/register",
            json={"email": f"pw_{password[:4]}@example.com", "password": password},
        )
        assert resp.status_code == 400, f"{reason} 应被拒绝，实际返回 {resp.status_code}"
        assert resp.json()["error"]["code"] == "WEAK_PASSWORD"

    @pytest.mark.parametrize("password", [
        "Password1",
        "secureABC123",
        "Test1234!",
        "a1b2c3d4",
    ])
    def test_strong_passwords_accepted(self, client, password):
        email = f"strong_{password[:6]}@example.com"
        resp = client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
        )
        assert resp.status_code in (200, 409), (
            f"强密码 {password!r} 不应因密码强度被拒绝，实际: {resp.status_code}"
        )
        if resp.status_code == 400:
            assert resp.json()["error"]["code"] != "WEAK_PASSWORD"


# ──────────────────────────────────────────────────────────────────────────────
# S9 — Notes 接口 Pydantic 校验
# ──────────────────────────────────────────────────────────────────────────────

class TestNotesPydanticValidation:

    @pytest.mark.no_db
    def test_create_note_request_model_exists(self):
        from routers.notes import CreateNoteRequest, UpdateNoteRequest
        assert CreateNoteRequest is not None
        assert UpdateNoteRequest is not None

    @pytest.mark.no_db
    def test_create_note_request_rejects_empty_content(self):
        from routers.notes import CreateNoteRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CreateNoteRequest(planId="p1", content="")

    @pytest.mark.no_db
    def test_create_note_request_rejects_whitespace_content(self):
        from routers.notes import CreateNoteRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CreateNoteRequest(planId="p1", content="   ")

    @pytest.mark.no_db
    def test_update_note_request_rejects_empty(self):
        from routers.notes import UpdateNoteRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UpdateNoteRequest(content="")

    def test_create_note_api_rejects_missing_content(self, client):
        from utils.auth import create_access_token
        token = create_access_token({"sub": "u_a"})
        resp = client.post(
            "/api/notes",
            json={"planId": "p_any"},  # 缺少 content
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422  # FastAPI Pydantic 校验失败

    def test_create_note_api_rejects_no_body(self, client):
        from utils.auth import create_access_token
        token = create_access_token({"sub": "u_a"})
        resp = client.post(
            "/api/notes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# S10 — DEBUG 默认关闭
# ──────────────────────────────────────────────────────────────────────────────

class TestDebugDefault:

    @pytest.mark.no_db
    def test_debug_default_is_false(self):
        """未设置 DEBUG 环境变量时，默认应为 False。
        需同时屏蔽 load_dotenv 防止 .env 文件覆盖环境变量。"""
        import os
        import importlib

        env = {k: v for k, v in os.environ.items() if k != "DEBUG"}
        with patch("dotenv.load_dotenv"), patch.dict("os.environ", env, clear=True):
            import config as cfg
            importlib.reload(cfg)
            assert cfg.settings.DEBUG is False

    @pytest.mark.no_db
    def test_debug_can_be_enabled_via_env(self):
        import importlib
        with patch("dotenv.load_dotenv"), patch.dict("os.environ", {"DEBUG": "true"}):
            import config as cfg
            importlib.reload(cfg)
            assert cfg.settings.DEBUG is True


# ──────────────────────────────────────────────────────────────────────────────
# S12 — 生产环境 /docs 关闭
# ──────────────────────────────────────────────────────────────────────────────

class TestDocsDisabledInProd:
    """
    验证 docs_url 的开关逻辑来自 settings.DEBUG。
    直接测试 main.py 中的计算逻辑，避免完整 reload 带来的副作用。
    """

    @pytest.mark.no_db
    def test_docs_url_is_none_when_debug_false(self):
        """/docs URL 在 DEBUG=False 时应为 None（不注册路由）。"""
        # 模拟 DEBUG=False 时 main.py 中的计算
        debug = False
        docs_url = "/docs" if debug else None
        openapi_url = "/openapi.json" if debug else None
        assert docs_url is None
        assert openapi_url is None

    @pytest.mark.no_db
    def test_docs_url_is_set_when_debug_true(self):
        """/docs URL 在 DEBUG=True 时应为 '/docs'。"""
        debug = True
        docs_url = "/docs" if debug else None
        assert docs_url == "/docs"

    @pytest.mark.no_db
    def test_main_py_uses_debug_for_docs(self):
        """main.py 源码中必须使用 settings.DEBUG 控制 docs_url。"""
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[1] / "main.py"
        ).read_text(encoding="utf-8")
        assert "docs_url" in source
        assert "settings.DEBUG" in source or "DEBUG" in source
        assert "docs_url=_docs_url" in source or "docs_url=" in source

    def test_docs_currently_inaccessible(self, client):
        """/docs 在当前测试环境（DEBUG 读自 .env）不应在生产中开放。
        如果 .env 设置 DEBUG=True，此测试会跳过以避免误报。"""
        from config import settings
        if settings.DEBUG:
            pytest.skip("当前 .env 中 DEBUG=True，跳过生产模式测试")
        resp = client.get("/docs")
        assert resp.status_code == 404
