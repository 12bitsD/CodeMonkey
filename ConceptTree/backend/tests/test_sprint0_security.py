"""
Sprint 0 安全修复测试
覆盖：
  S2  — database.py schema 白名单验证（阻断 SQL 注入）
  L1  — auth.py JWT 配置来源（必须读自 config.py）
  Hook— .claude/hooks/ 脚本单元测试（不依赖 DB）

运行方式：
  cd backend
  pytest tests/test_sprint0_security.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

BACKEND = Path(__file__).resolve().parents[1]
HOOKS = BACKEND.parent / ".claude" / "hooks"
PYTHON = sys.executable


# ──────────────────────────────────────────────────────────────────────────────
# S2 — database.py schema 白名单验证
# ──────────────────────────────────────────────────────────────────────────────

class TestSchemaWhitelist:
    """_VALID_SCHEMA_RE 白名单正则必须拒绝恶意 schema 名称。"""

    @pytest.fixture(autouse=True)
    def import_module(self):
        import importlib
        import database
        importlib.reload(database)
        self.database = database

    def _validate(self, schema: str) -> bool:
        return bool(self.database._VALID_SCHEMA_RE.match(schema))

    # ── 合法名称 ──────────────────────────────────────────────────────────────
    @pytest.mark.no_db
    def test_valid_public(self):
        assert self._validate("public") is True

    @pytest.mark.no_db
    def test_valid_with_underscore(self):
        assert self._validate("my_schema") is True

    @pytest.mark.no_db
    def test_valid_alphanumeric(self):
        assert self._validate("schema01") is True

    @pytest.mark.no_db
    def test_valid_uppercase(self):
        assert self._validate("MySchema") is True

    # ── 注入攻击尝试 ──────────────────────────────────────────────────────────
    @pytest.mark.no_db
    def test_reject_sql_injection_semicolon(self):
        assert self._validate("public; DROP TABLE users--") is False

    @pytest.mark.no_db
    def test_reject_sql_injection_union(self):
        assert self._validate("public UNION SELECT") is False

    @pytest.mark.no_db
    def test_reject_starts_with_digit(self):
        assert self._validate("1schema") is False

    @pytest.mark.no_db
    def test_reject_dash(self):
        assert self._validate("my-schema") is False

    @pytest.mark.no_db
    def test_reject_dot(self):
        assert self._validate("public.secret") is False

    @pytest.mark.no_db
    def test_reject_empty(self):
        assert self._validate("") is False

    @pytest.mark.no_db
    def test_reject_single_quote(self):
        assert self._validate("schema'--") is False

    @pytest.mark.no_db
    def test_reject_too_long(self):
        # PostgreSQL identifier limit is 63 bytes; regex caps at 62 extra chars
        assert self._validate("a" * 65) is False

    def test_connect_raises_on_invalid_schema(self):
        """_connect() 必须在无效 schema 时抛出 ValueError，而非执行 SQL。"""
        import os
        import psycopg2

        with patch.dict(os.environ, {"DATABASE_SCHEMA": "evil; DROP TABLE--"}):
            with patch("psycopg2.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_connect.return_value = mock_conn
                with pytest.raises(ValueError, match="Invalid DATABASE_SCHEMA"):
                    self.database._connect()
                # 确认恶意 schema 从未被传入 execute()
                mock_conn.cursor.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# L1 — JWT 配置来源验证
# ──────────────────────────────────────────────────────────────────────────────

class TestJWTConfigSource:
    """auth.py 的 SECRET_KEY 必须来自 config.py，而非硬编码。"""

    @pytest.mark.no_db
    def test_secret_key_from_settings(self):
        from utils.auth import SECRET_KEY
        from config import settings
        assert SECRET_KEY == settings.JWT_SECRET_KEY

    @pytest.mark.no_db
    def test_algorithm_from_settings(self):
        from utils.auth import ALGORITHM
        from config import settings
        assert ALGORITHM == settings.JWT_ALGORITHM

    @pytest.mark.no_db
    def test_expire_days_from_settings(self):
        from utils.auth import ACCESS_TOKEN_EXPIRE_DAYS
        from config import settings
        assert ACCESS_TOKEN_EXPIRE_DAYS == settings.JWT_EXPIRE_DAYS

    @pytest.mark.no_db
    def test_no_literal_secret_in_source(self):
        """auth.py 源码中不得出现形如 SECRET_KEY = "literal..." 的硬编码。"""
        import re
        source = (BACKEND / "utils" / "auth.py").read_text(encoding="utf-8")
        hardcoded = re.search(
            r'^SECRET_KEY\s*=\s*["\'][^"\'\n]{4,}["\']',
            source,
            re.MULTILINE,
        )
        assert hardcoded is None, (
            f"Found hardcoded SECRET_KEY in auth.py: {hardcoded.group()}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Hook 脚本单元测试（无 DB、无网络）
# ──────────────────────────────────────────────────────────────────────────────

def _run_hook(script_name: str, stdin_data: dict) -> tuple[int, str]:
    """运行 hook 脚本，返回 (exit_code, stdout)。"""
    script = HOOKS / script_name
    if not script.exists():
        pytest.skip(f"Hook script not found: {script}")
    result = subprocess.run(
        [PYTHON, str(script)],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, result.stdout


class TestEnvWriteHook:
    """check_env_write.py — 阻断 .env 写入，放行 .env.example。"""

    @pytest.mark.no_db
    def test_blocks_env_write(self):
        code, out = _run_hook(
            "check_env_write.py",
            {"tool_name": "Write", "tool_input": {"file_path": "backend/.env"}},
        )
        assert code == 2, "应以 exit 2 阻断 .env 写入"
        data = json.loads(out)
        assert data["continue"] is False

    @pytest.mark.no_db
    def test_blocks_env_edit(self):
        code, out = _run_hook(
            "check_env_write.py",
            {"tool_name": "Edit", "tool_input": {"file_path": "/project/backend/.env"}},
        )
        assert code == 2

    @pytest.mark.no_db
    def test_allows_env_example(self):
        code, _ = _run_hook(
            "check_env_write.py",
            {"tool_name": "Write", "tool_input": {"file_path": "backend/.env.example"}},
        )
        assert code == 0, ".env.example 应被放行"

    @pytest.mark.no_db
    def test_allows_other_files(self):
        code, _ = _run_hook(
            "check_env_write.py",
            {"tool_name": "Write", "tool_input": {"file_path": "backend/config.py"}},
        )
        assert code == 0


class TestSqlFstringHook:
    """check_sql_fstring.py — 检测 execute() 中的 f-string。"""

    @pytest.mark.no_db
    def test_skips_non_database_file(self, tmp_path):
        code, out = _run_hook(
            "check_sql_fstring.py",
            {"tool_name": "Edit", "tool_input": {"file_path": str(tmp_path / "other.py")}},
        )
        assert code == 0
        assert "systemMessage" not in out

    @pytest.mark.no_db
    def test_warns_on_unguarded_fstring(self, tmp_path):
        bad_file = tmp_path / "database.py"
        bad_file.write_text(
            'def q(conn, name):\n    conn.cursor().execute(f"SELECT * FROM {name}")\n',
            encoding="utf-8",
        )
        code, out = _run_hook(
            "check_sql_fstring.py",
            {"tool_name": "Edit", "tool_input": {"file_path": str(bad_file)}},
        )
        assert code == 0  # 非阻断，只警告
        data = json.loads(out)
        assert "systemMessage" in data
        assert "f-string" in data["systemMessage"]

    @pytest.mark.no_db
    def test_clean_file_produces_no_output(self, tmp_path):
        clean_file = tmp_path / "database.py"
        clean_file.write_text(
            'def q(conn, name):\n    conn.cursor().execute("SELECT * FROM public")\n',
            encoding="utf-8",
        )
        code, out = _run_hook(
            "check_sql_fstring.py",
            {"tool_name": "Edit", "tool_input": {"file_path": str(clean_file)}},
        )
        assert code == 0
        assert out.strip() == ""


class TestJwtHardcodeHook:
    """check_jwt_hardcode.py — 检测 auth.py 中硬编码的 SECRET_KEY。"""

    @pytest.mark.no_db
    def test_no_warning_for_current_auth_py(self):
        """当前 auth.py 应通过检测（无硬编码）。"""
        code, out = _run_hook("check_jwt_hardcode.py", {})
        assert code == 0
        assert "WARNING" not in out
