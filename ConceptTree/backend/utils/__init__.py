"""
Shared backend utilities for authentication, security, and ID generation.

This package bundles three focused utility modules so every other backend
module can import them from a single, predictable location.

Modules:
    auth        — JWT token creation and verification; FastAPI dependency for
                  extracting the current user's ID from a protected request.
    password    — PBKDF2-SHA256 password hashing and plain-text verification.
    id_generator — Prefixed, UUID4-based ID generation for users and profiles.

Typical usage::

    from backend.utils.auth import get_current_user_id
    from backend.utils.password import hash_password, verify_password
    from backend.utils.id_generator import generate_user_id
"""
