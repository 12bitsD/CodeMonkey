"""
User profile router — lets authenticated users read and update their learning profile.

This router exposes two endpoints under the ``/api/user`` prefix:

- ``GET /profile`` — retrieve the full learning profile for the current user
- ``PUT /profile`` — partially update editable profile fields

**Profile schema** (returned in ``data``):

.. code-block:: json

    {
      "occupation":        "string | null",
      "education":         "string | null",
      "programmingLevel":  "string",
      "mathLevel":         "string",
      "abilities":         ["string", ...],
      "masteredKnowledge": ["string", ...]
    }

**Read-only field:** ``masteredKnowledge`` is managed exclusively by the AI
tutoring engine and is silently ignored in ``PUT`` requests.

**Storage note:** ``abilities`` and ``masteredKnowledge`` are stored as
JSON-serialised strings in SQLite and are automatically deserialised to
Python lists before being returned in responses.
"""

import json
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from database import get_db_context
from models import UpdateProfileRequest
from utils.auth import get_current_user_id

router = APIRouter(prefix="/api/user", tags=["用户"])


def parse_json_field(field_value, default=None):
    """Safely deserialise a JSON-serialised list/dict stored in SQLite.

    SQLite does not have a native array type, so list fields are stored as
    JSON strings. This helper handles three cases:
    - ``None`` / empty → returns ``default``
    - Already-parsed Python ``list`` or ``dict`` → returned as-is
    - Raw JSON string → parsed with ``json.loads``

    Args:
        field_value: The raw value from the database column. May be ``None``,
            an already-parsed ``list``/``dict``, or a JSON string.
        default: Value to return when ``field_value`` is falsy.
            Defaults to an empty list ``[]``.

    Returns:
        A Python ``list`` or ``dict``, never a raw JSON string.
    """
    if default is None:
        default = []
    if not field_value:
        return default
    if isinstance(field_value, (list, dict)):
        return field_value
    return json.loads(field_value)


@router.get("/profile")
def get_profile(user_id: str = Depends(get_current_user_id)):
    """Return the full learning profile for the authenticated user.

    Reads from the ``user_profiles`` table. JSON array fields (``abilities``,
    ``masteredKnowledge``) are deserialised from SQLite strings before
    being returned.

    Args:
        user_id: Injected automatically from the ``Authorization`` header via
            the ``get_current_user_id`` dependency.

    Returns:
        200 JSON::

            {
              "success": true,
              "data": {
                "occupation":        "string | null",
                "education":         "string | null",
                "programmingLevel":  "string",
                "mathLevel":         "string",
                "abilities":         ["string", ...],
                "masteredKnowledge": ["string", ...]
              }
            }

    Raises:
        401: Missing or invalid ``Authorization`` header.
        404 PROFILE_NOT_FOUND: No profile row exists for this user ID.
            (Should not occur for accounts created via ``POST /api/auth/register``.)
    """
    with get_db_context() as db:
        profile = db.execute(
            """SELECT occupation, education, programming_level, math_level, 
                      abilities, mastered_knowledge
               FROM user_profiles WHERE user_id = ?""",
            (user_id,),
        ).fetchone()

        if not profile:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": {"code": "PROFILE_NOT_FOUND", "message": "用户画像不存在"},
                },
            )

        abilities = parse_json_field(profile["abilities"])
        mastered_knowledge = parse_json_field(profile["mastered_knowledge"])

        return {
            "success": True,
            "data": {
                "occupation": profile["occupation"],
                "education": profile["education"],
                "programmingLevel": profile["programming_level"],
                "mathLevel": profile["math_level"],
                "abilities": abilities,
                "masteredKnowledge": mastered_knowledge,
            },
        }


@router.put("/profile")
def update_profile(
    req: UpdateProfileRequest, user_id: str = Depends(get_current_user_id)
):
    """Partially update the authenticated user's learning profile and return the result.

    Only fields included in the request body are written to the database
    (partial/PATCH-style semantics despite the ``PUT`` verb). The
    ``masteredKnowledge`` field is **always excluded** — it is managed by the
    AI tutoring engine and cannot be set by the user directly.

    If the request body contains no recognised fields, the profile is unchanged
    and the current profile is returned as-is.

    Args:
        req: Partial update payload. All fields are optional:
            - ``occupation``       (str | None)
            - ``education``        (str | None)
            - ``programmingLevel`` (str | None)
            - ``mathLevel``        (str | None)
            - ``abilities``        (list | None)
        user_id: Injected automatically from the ``Authorization`` header via
            the ``get_current_user_id`` dependency.

    Returns:
        200 JSON — the full updated profile (same shape as ``GET /profile``)::

            {
              "success": true,
              "data": {
                "occupation":        "string | null",
                "education":         "string | null",
                "programmingLevel":  "string",
                "mathLevel":         "string",
                "abilities":         ["string", ...],
                "masteredKnowledge": ["string", ...]
              }
            }

    Raises:
        401: Missing or invalid ``Authorization`` header.
        404 PROFILE_NOT_FOUND: No profile row exists for this user ID.
    """
    with get_db_context() as db:
        # Confirm the profile exists before attempting an update
        profile = db.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()

        if not profile:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": {"code": "PROFILE_NOT_FOUND", "message": "用户画像不存在"},
                },
            )

        # Build a dynamic SET clause from only the fields present in the request
        updates = []
        params = []

        if req.occupation is not None:
            updates.append("occupation = ?")
            params.append(req.occupation)

        if req.education is not None:
            updates.append("education = ?")
            params.append(req.education)

        if req.programmingLevel is not None:
            updates.append("programming_level = ?")
            params.append(req.programmingLevel)

        if req.mathLevel is not None:
            updates.append("math_level = ?")
            params.append(req.mathLevel)

        if req.abilities is not None:
            updates.append("abilities = ?")
            params.append(req.abilities)

        # masteredKnowledge字段不允许更新（只读）

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)

            set_clause = ", ".join(updates)
            query = f"UPDATE user_profiles SET {set_clause} WHERE user_id = ?"
            db.execute(query, params)
            db.commit()

        # 返回更新后的画像
        updated_profile = db.execute(
            """SELECT occupation, education, programming_level, math_level, 
                      abilities, mastered_knowledge
               FROM user_profiles WHERE user_id = ?""",
            (user_id,),
        ).fetchone()

        abilities = parse_json_field(updated_profile["abilities"])
        mastered_knowledge = parse_json_field(updated_profile["mastered_knowledge"])

        return {
            "success": True,
            "data": {
                "occupation": updated_profile["occupation"],
                "education": updated_profile["education"],
                "programmingLevel": updated_profile["programming_level"],
                "mathLevel": updated_profile["math_level"],
                "abilities": abilities,
                "masteredKnowledge": mastered_knowledge,
            },
        }
