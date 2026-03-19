"""
Password hashing and verification using PBKDF2-SHA256.

Never store or compare plain-text passwords — always hash first with
``hash_password`` and verify at login time with ``verify_password``.

Key facts:
    1. PBKDF2-SHA256 is a salted, iterative hash — brute-force resistant
       and safe for long-term password storage.
    2. ``passlib`` transparently handles salt generation and embedding,
       so callers need only pass the plain text.
    3. Hash output is self-describing: the algorithm and parameters are
       encoded into the hash string, enabling automatic upgrade paths.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a secure, salted hash of ``password`` for database storage.

    Delegates to ``passlib``'s PBKDF2-SHA256 scheme, which automatically
    generates a random salt and embeds it in the returned string.

    Args:
        password: The plain-text password provided by the user.

    Returns:
        A self-describing hash string (algorithm + salt + digest) safe
        to persist in the database. Example format::

            $pbkdf2-sha256$29000$<salt>$<digest>
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` if ``plain_password`` matches ``hashed_password``.

    Extracts the salt and parameters from ``hashed_password``, re-hashes
    ``plain_password`` with the same settings, and compares the results
    using a timing-safe equality check.

    Args:
        plain_password: The raw password submitted by the user at login.
        hashed_password: The stored hash previously produced by
            ``hash_password``.

    Returns:
        ``True`` if the password matches; ``False`` otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)
