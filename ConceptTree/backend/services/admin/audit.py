from __future__ import annotations

from typing import Any

from database import DbSession


def record_admin_read(
    db: DbSession,
    *,
    admin_user_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.execute(
        """
        INSERT INTO admin_audit_logs (
          admin_user_id, action, resource_type, resource_id, request_id, metadata
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            admin_user_id,
            action,
            resource_type,
            resource_id,
            request_id,
            metadata or {},
        ),
    )
    db.commit()
