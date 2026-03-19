"""
Prefixed, UUID4-based ID generation for database entities.

Every ID is a short string with a type prefix, making records immediately
identifiable in logs, API responses, and the database without schema lookups.

Key facts:
    1. Prefix encodes the entity type: ``u_`` for users, ``p_`` for profiles.
    2. The 12-character hex suffix comes from UUID4, giving ~281 trillion
       unique combinations — collision probability is negligible in practice.
    3. One function per entity type prevents accidental cross-entity ID reuse.
"""

import uuid


def generate_user_id() -> str:
    """Return a unique, human-readable ID for a new user record.

    Produces an ID of the form ``u_<12 hex chars>``, e.g. ``u_3f8a9b2c1d4e``.
    The ``u_`` prefix distinguishes user IDs from other entity IDs at a glance.

    Returns:
        A unique string ID, 14 characters long (prefix + 12 hex chars).
    """
    return f"u_{uuid.uuid4().hex[:12]}"


def generate_profile_id() -> str:
    """Return a unique, human-readable ID for a new user-profile record.

    Produces an ID of the form ``p_<12 hex chars>``, e.g. ``p_a1b2c3d4e5f6``.
    The ``p_`` prefix distinguishes profile IDs from user IDs and other entities.

    Returns:
        A unique string ID, 14 characters long (prefix + 12 hex chars).
    """
    return f"p_{uuid.uuid4().hex[:12]}"
