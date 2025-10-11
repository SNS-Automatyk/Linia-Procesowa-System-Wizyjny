import os
from datetime import datetime, timezone
from typing import List, Tuple
from urllib.parse import quote

from fastapi import APIRouter, Query

from src.static_assets import ANNOTATED_IMAGES_DIR


router = APIRouter()

_IMAGE_EXTENSIONS: Tuple[str, ...] = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp")


def _collect_image_files() -> List[tuple[str, float]]:
    if not os.path.isdir(ANNOTATED_IMAGES_DIR):
        return []

    entries: List[tuple[str, float]] = []
    for name in os.listdir(ANNOTATED_IMAGES_DIR):
        path = os.path.join(ANNOTATED_IMAGES_DIR, name)
        if not os.path.isfile(path):
            continue
        if os.path.splitext(name)[1].lower() not in _IMAGE_EXTENSIONS:
            continue
        try:
            stat_result = os.stat(path)
        except OSError:
            continue
        entries.append((name, stat_result.st_mtime))

    entries.sort(key=lambda item: item[1], reverse=True)
    return entries


@router.get("/annotated-images")
def list_annotated_images(
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
):
    files = _collect_image_files()
    sliced = files[skip : skip + limit] if files else []
    images = []

    for filename, mtime in sliced:
        images.append(
            {
                "filename": filename,
                "url": f"/annotated-images/{quote(filename)}",
                "modified_at": datetime.fromtimestamp(
                    mtime, tz=timezone.utc
                ).isoformat(),
            }
        )

    return {"images": images, "total": len(files)}
