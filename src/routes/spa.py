import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

from src.static_assets import DIST


router = APIRouter()


@router.get("/{full_path:path}")
def spa(full_path: str):
    return FileResponse(os.path.join(DIST, "index.html"))
