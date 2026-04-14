from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, field_validator

from database import get_db
from utils.auth import get_current_user_id


class CreateNoteRequest(BaseModel):
    planId: str
    nodeId: Optional[str] = None
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v


class UpdateNoteRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v

router = APIRouter(prefix="/api", tags=["notes"])


def format_date(dt_value) -> str:
    """Format datetime string to friendly date like '12/28'"""
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
    body: CreateNoteRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    planId = body.planId
    nodeId = body.nodeId
    content = body.content

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
    body: UpdateNoteRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    content = body.content

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
