"""Media upload — backs the image-occlusion editor (§14 Phase 4).

Images are uploaded *before* the note exists (you need to see the picture to
draw masks on it), so this is a standalone endpoint rather than part of note
creation. Files land under MEDIA_ROOT/<user_id>/ and are served by the /media
static mount.
"""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.models import User
from app.routers.deps import current_user

router = APIRouter(prefix="/api", tags=["media"])

MAX_BYTES = 20 * 1024 * 1024
ALLOWED = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
}

# How much of the file is needed to recognise it.
_SNIFF_BYTES = 16


def sniff_media_type(head: bytes) -> str | None:
    """The type the bytes actually are, from their signature.

    The declared Content-Type and the filename are both chosen by the client,
    so neither decides what gets stored: a script uploaded as "image/png"
    would otherwise sit on this origin with an image extension.
    """
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    if head.startswith(b"OggS"):
        return "audio/ogg"
    # MP3: an ID3v2 tag, or a bare MPEG audio frame (11 sync bits, layer != 0).
    if head.startswith(b"ID3"):
        return "audio/mpeg"
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0 and (head[1] & 0x06) != 0:
        return "audio/mpeg"
    return None


def _directory_bytes(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(f.stat().st_size for f in directory.iterdir() if f.is_file())


@router.post("/media", status_code=201)
async def upload_media(
    file: UploadFile = File(...), user: User = Depends(current_user)
) -> dict:
    head = await file.read(_SNIFF_BYTES)
    content_type = sniff_media_type(head)
    if content_type is None:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"unsupported type {file.content_type!r}; allowed: {', '.join(sorted(ALLOWED))}",
        )

    dest_dir = Path(settings.media_root) / str(user.id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    quota = settings.media_quota_mb * 1024 * 1024
    used = await asyncio.to_thread(_directory_bytes, dest_dir) if quota else 0
    if quota and used >= quota:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"media storage is full ({settings.media_quota_mb} MB); delete unused media first",
        )

    # Random server-side name: the uploaded filename is never used to build a
    # path, so a crafted name can't escape the user's media directory.
    name = f"{secrets.token_urlsafe(12)}{ALLOWED[content_type]}"
    dest = dest_dir / name

    size = 0
    chunk = head
    with dest.open("wb") as fh:
        while chunk:
            size += len(chunk)
            if size > MAX_BYTES or (quota and used + size > quota):
                fh.close()
                dest.unlink(missing_ok=True)
                detail = (
                    "file exceeds 20 MB"
                    if size > MAX_BYTES
                    else f"media storage is full ({settings.media_quota_mb} MB)"
                )
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail)
            fh.write(chunk)
            chunk = await file.read(1 << 20)

    return {
        "url": f"/media/{user.id}/{name}",
        "kind": "audio" if content_type.startswith("audio/") else "image",
        "bytes": size,
    }
