"""Media upload — backs the image-occlusion editor (§14 Phase 4).

Images are uploaded *before* the note exists (you need to see the picture to
draw masks on it), so this is a standalone endpoint rather than part of note
creation. Files land under MEDIA_ROOT/<user_id>/ and are served by the /media
static mount.
"""

from __future__ import annotations

import mimetypes
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


@router.post("/media", status_code=201)
async def upload_media(
    file: UploadFile = File(...), user: User = Depends(current_user)
) -> dict:
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED:
        guessed, _ = mimetypes.guess_type(file.filename or "")
        content_type = (guessed or "").lower()
    if content_type not in ALLOWED:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"unsupported type {file.content_type!r}; allowed: {', '.join(sorted(ALLOWED))}",
        )

    # Random server-side name: the uploaded filename is never used to build a
    # path, so a crafted name can't escape the user's media directory.
    name = f"{secrets.token_urlsafe(12)}{ALLOWED[content_type]}"
    dest_dir = Path(settings.media_root) / str(user.id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name

    size = 0
    with dest.open("wb") as fh:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            if size > MAX_BYTES:
                fh.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file exceeds 20 MB"
                )
            fh.write(chunk)

    return {
        "url": f"/media/{user.id}/{name}",
        "kind": "audio" if content_type.startswith("audio/") else "image",
        "bytes": size,
    }
