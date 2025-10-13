from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.state import camera


router = APIRouter()


@router.get("/camera")
async def camera_stream():
    if camera:
        return StreamingResponse(
            camera.mjpeg_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )
    else:
        return 
