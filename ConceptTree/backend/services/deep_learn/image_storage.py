"""Supabase Storage upload for DALL-E generated images."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

import httpx

from config import settings

logger = logging.getLogger(__name__)

_BUCKET = "deep_learn_images"
_LOCAL_IMAGE_ROOT = Path(__file__).resolve().parents[2] / "static" / _BUCKET


def _save_local_image(user_id: str, session_id: str, image_bytes: bytes, file_ext: str) -> str:
    safe_ext = file_ext.strip(".") or "png"
    relative_path = Path(user_id) / session_id / f"{uuid4()}.{safe_ext}"
    target = _LOCAL_IMAGE_ROOT / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(image_bytes)
    base_url = settings.BACKEND_PUBLIC_BASE_URL.rstrip("/")
    return f"{base_url}/static/{_BUCKET}/{relative_path.as_posix()}"


async def upload_image(
    user_id: str,
    session_id: str,
    image_bytes: bytes,
    *,
    file_ext: str = "png",
) -> str:
    """Upload image to Supabase Storage bucket, return public URL."""
    supabase_url = settings.SUPABASE_URL
    service_key = settings.SUPABASE_SERVICE_ROLE_KEY

    if not supabase_url or not service_key:
        logger.warning("Supabase storage is not configured; saving image locally")
        return _save_local_image(user_id, session_id, image_bytes, file_ext)

    path = f"{user_id}/{session_id}/{uuid4()}.{file_ext}"
    upload_url = f"{supabase_url}/storage/v1/object/{_BUCKET}/{path}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            upload_url,
            content=image_bytes,
            headers={
                "Authorization": f"Bearer {service_key}",
                "Content-Type": f"image/{file_ext}",
            },
        )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Supabase Storage upload failed: {response.status_code} {response.text}"
        )

    public_url = f"{supabase_url}/storage/v1/object/public/{_BUCKET}/{path}"
    return public_url
