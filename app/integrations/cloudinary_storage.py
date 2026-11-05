import asyncio
import logging

import cloudinary
import cloudinary.uploader

from app.core import messages
from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailable

logger = logging.getLogger("app.cloudinary")

UPLOAD_FOLDER = "nishchit/products"

_configured = False


def is_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.cloudinary_cloud_name
        and settings.cloudinary_api_key
        and settings.cloudinary_api_secret
    )


def _ensure_configured() -> None:
    global _configured
    if not is_configured():
        raise ServiceUnavailable(
            messages.IMAGE_UPLOAD_NOT_CONFIGURED, error_code="IMAGE_UPLOAD_NOT_CONFIGURED"
        )
    if not _configured:
        settings = get_settings()
        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )
        _configured = True


def _upload_sync(content: bytes) -> tuple[str, str]:
    result = cloudinary.uploader.upload(content, folder=UPLOAD_FOLDER)
    return result["secure_url"], result["public_id"]


def _destroy_sync(public_id: str) -> None:
    cloudinary.uploader.destroy(public_id)


async def upload_image(content: bytes) -> tuple[str, str]:
    """Uploads image bytes to Cloudinary, returns (secure_url, public_id)."""
    _ensure_configured()
    return await asyncio.to_thread(_upload_sync, content)


async def delete_image(public_id: str) -> None:
    if not is_configured():
        return
    try:
        await asyncio.to_thread(_destroy_sync, public_id)
    except Exception:
        logger.exception("Failed to delete Cloudinary image %s", public_id)
