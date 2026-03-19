"""
Notes router — full CRUD for user-authored notes tied to learning plan nodes.

Each note is anchored to a specific node (a topic/concept) within a learning plan.
This router exposes four endpoints under the ``/api`` prefix:

- ``GET    /notes``            — list the current user's notes, with optional filters
- ``POST   /notes``            — create a new note on a plan node
- ``PUT    /notes/{note_id}``  — update the content of an existing note
- ``DELETE /notes/{note_id}``  — permanently delete a note

**Ownership enforcement:** Every write endpoint (POST, PUT, DELETE) verifies
that the target resource belongs to the authenticated user and returns
``403 Forbidden`` if it does not.

**Note shape** (as returned in ``data``):

.. code-block:: json

    {
      "id":        "note_<12-char hex>",
      "planId":    "<plan_id>",
      "planTitle": "<plan title>",
      "nodeId":    "<node_id>",
      "nodeName":  "<node name>",
      "content":   "User-written text",
      "date":      "12/28",
      "createdAt": "2024-12-28T10:30:00Z"
    }

``date`` is a short ``M/D`` display string derived from ``createdAt`` and is
provided as a convenience for UI date labels.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime
import uuid

from database import get_db
from utils.auth import get_current_user_id

router = APIRouter(prefix="/api", tags=["notes"])


def format_date(dt_value) -> str:
    """Convert a datetime value to a short ``M/D`` display string (e.g. ``'12/28'``).

    Handles three input types: a ``datetime`` object, an ISO 8601 string
    (with or without a trailing ``Z``), or any other string (falls back to
    returning the first 10 characters of the raw value).

    Args:
        dt_value: A ``datetime`` object, an ISO 8601 string, or ``None``.

    Returns:
        A ``"month/day"`` string such as ``"12/28"``, the first 10 characters
        of the raw string if parsing fails, or ``""`` if the input is falsy.
    """
    if not dt_value:
        return ""
    try:
        if isinstance(dt_value, datetime):
            dt = dt_value
        else:
            dt = datetime.fromisoformat(str(dt_value).replace("Z", "+00:00"))
        return f"{dt.month}/{dt.day}"
    except (ValueError, TypeError):
        raw = str(dt_value)
        return raw[:10] if raw else ""


@router.get("/notes")
def get_notes(
    planId: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Return all notes belonging to the authenticated user, ordered newest first.

    Joins ``notes`` with ``plans`` and ``nodes`` to include human-readable
    plan titles and node names alongside each note. Both ``planId`` and
    ``search`` filters are applied when provided; they can be combined.

    Args:
        planId: (optional query param) Restrict results to notes inside a
            specific learning plan.
        search: (optional query param) Case-insensitive substring filter
            applied to note ``content`` (SQL ``LIKE '%search%'``).
        current_user_id: Injected from the ``Authorization`` header.
        db: Injected database connection.

    Returns:
        200 JSON::

            {
              "success": true,
              "data": {
                "notes": [ { ...note shape... }, ... ],
                "total": 12
              }
            }

    Raises:
        401: Missing or invalid ``Authorization`` header.
    """
    query = """
        SELECT 
            n.id, n.plan_id, n.node_id, n.content, n.created_at,
            p.title as plan_title,
            nd.name as node_name
        FROM notes n
        JOIN plans p ON n.plan_id = p.id
        JOIN nodes nd ON n.node_id = nd.id
        WHERE n.user_id = ?
    """
    params = [current_user_id]

    if planId:
        query += " AND n.plan_id = ?"
        params.append(planId)

    if search:
        query += " AND n.content LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY n.created_at DESC"

    rows = db.execute(query, params).fetchall()

    notes = []
    for row in rows:
        notes.append(
            {
                "id": row["id"],
                "planId": row["plan_id"],
                "planTitle": row["plan_title"],
                "nodeId": row["node_id"],
                "nodeName": row["node_name"],
                "content": row["content"],
                "date": format_date(row["created_at"]),
                "createdAt": row["created_at"],
            }
        )

    return {"success": True, "data": {"notes": notes, "total": len(notes)}}


@router.post("/notes")
def create_note(
    body: dict,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Create a new note attached to a specific node within a learning plan.

    Verifies that both the plan and the node exist and that the plan belongs
    to the authenticated user before inserting. Note IDs are generated as
    ``note_<12-char UUID hex>`` (e.g. ``note_3f8a2c1b09d4``).

    Args:
        body: JSON request body with fields:
            - ``planId``  (str, required) — ID of the learning plan.
            - ``nodeId``  (str, required) — ID of the node within that plan.
            - ``content`` (str, required) — Note text; must be non-empty after stripping.
        current_user_id: Injected from the ``Authorization`` header.
        db: Injected database connection.

    Returns:
        200 JSON::

            {
              "success": true,
              "data": {
                "id":        "note_3f8a2c1b09d4",
                "planId":    "<plan_id>",
                "nodeId":    "<node_id>",
                "content":   "My note text",
                "date":      "12/28",
                "createdAt": "2024-12-28T10:30:00.000000Z"
              }
            }

    Raises:
        400 CONTENT_REQUIRED:  ``content`` is missing or blank.
        401:                   Missing or invalid ``Authorization`` header.
        403 FORBIDDEN:         The specified plan belongs to a different user.
        404 PLAN_NOT_FOUND:    No plan exists with the given ``planId``.
        404 NODE_NOT_FOUND:    No node with ``nodeId`` exists inside ``planId``.
    """
    planId = body.get("planId")
    nodeId = body.get("nodeId")
    content = body.get("content")

    if not content or not content.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": "CONTENT_REQUIRED",
                    "message": "Content is required",
                },
            },
        )

    plan = db.execute(
        "SELECT user_id FROM plans WHERE id = ?",
        (planId,),
    ).fetchone()
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "PLAN_NOT_FOUND",
                    "message": "Plan not found",
                },
            },
        )
    if plan["user_id"] != current_user_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Forbidden"},
        )

    node = db.execute(
        "SELECT id FROM nodes WHERE id = ? AND plan_id = ?", (nodeId, planId)
    ).fetchone()
    if not node:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "NODE_NOT_FOUND",
                    "message": "Node not found",
                },
            },
        )

    note_id = f"note_{uuid.uuid4().hex[:12]}"
    user_id = current_user_id
    now = datetime.utcnow().isoformat() + "Z"

    db.execute(
        """INSERT INTO notes (id, plan_id, node_id, user_id, content, 
           created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (note_id, planId, nodeId, user_id, content, now, now),
    )
    db.commit()

    return {
        "success": True,
        "data": {
            "id": note_id,
            "planId": planId,
            "nodeId": nodeId,
            "content": content,
            "date": format_date(now),
            "createdAt": now,
        },
    }


@router.put("/notes/{note_id}")
def update_note(
    note_id: str,
    body: dict,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Replace the content of an existing note and return the updated record.

    Only the ``content`` field can be updated. Ownership is verified before
    writing: a user cannot modify another user's notes.

    Args:
        note_id: Path parameter — the ID of the note to update
            (format: ``note_<12-char hex>``).
        body: JSON request body with fields:
            - ``content`` (str, required) — Replacement text; must be non-empty
              after stripping whitespace.
        current_user_id: Injected from the ``Authorization`` header.
        db: Injected database connection.

    Returns:
        200 JSON::

            {
              "success": true,
              "data": {
                "id":        "<note_id>",
                "content":   "Updated text",
                "updatedAt": "2024-12-28T11:00:00.000000Z"
              }
            }

    Raises:
        400 CONTENT_REQUIRED:  ``content`` is missing or blank.
        401:                   Missing or invalid ``Authorization`` header.
        403 FORBIDDEN:         This note belongs to a different user.
        404 NOTE_NOT_FOUND:    No note exists with the given ``note_id``.
    """
    content = body.get("content")

    if not content or not content.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": "CONTENT_REQUIRED",
                    "message": "Content is required",
                },
            },
        )

    note = db.execute(
        "SELECT id, user_id FROM notes WHERE id = ?",
        (note_id,),
    ).fetchone()
    if not note:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "NOTE_NOT_FOUND",
                    "message": "Note not found",
                },
            },
        )
    if note["user_id"] != current_user_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Forbidden"},
        )

    now = datetime.utcnow().isoformat() + "Z"
    db.execute(
        "UPDATE notes SET content = ?, updated_at = ? WHERE id = ?",
        (content, now, note_id),
    )
    db.commit()

    return {
        "success": True,
        "data": {"id": note_id, "content": content, "updatedAt": now},
    }


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Permanently delete a note after verifying the caller owns it.

    This operation is irreversible. Ownership is verified before deletion:
    a user cannot delete another user's notes.

    Args:
        note_id: Path parameter — the ID of the note to delete
            (format: ``note_<12-char hex>``).
        current_user_id: Injected from the ``Authorization`` header.
        db: Injected database connection.

    Returns:
        200 JSON::

            {"success": true, "data": {"message": "笔记已删除"}}

    Raises:
        401:                 Missing or invalid ``Authorization`` header.
        403 FORBIDDEN:       This note belongs to a different user.
        404 NOTE_NOT_FOUND:  No note exists with the given ``note_id``.
    """
    note = db.execute(
        "SELECT id, user_id FROM notes WHERE id = ?",
        (note_id,),
    ).fetchone()
    if not note:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "NOTE_NOT_FOUND",
                    "message": "Note not found",
                },
            },
        )
    if note["user_id"] != current_user_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Forbidden"},
        )

    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()

    return {"success": True, "data": {"message": "笔记已删除"}}
