import asyncio
import logging
from contextlib import suppress
from typing import Optional

from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect

from src.logging_utils import InMemoryLogHandler, setup_in_memory_logging
from src.state import shutdown_event


router = APIRouter()


@router.get("/logs")
def get_logs(
    request: Request,
    limit: int = Query(default=200, ge=1, le=2000),
    level: Optional[str] = Query(default=None),
):
    """Return recent logs captured from the system_wizyjny logger."""
    handler: InMemoryLogHandler = getattr(request.app.state, "log_handler", None)
    if handler is None:
        handler = setup_in_memory_logging(
            "system_wizyjny", level=logging.INFO, maxlen=100
        )
        request.app.state.log_handler = handler

    levelno = None
    if level:
        level_upper = level.upper()
        if hasattr(logging, level_upper):
            levelno = getattr(logging, level_upper)
        else:
            return {"error": f"Unknown level: {level}"}

    return {"logs": handler.get_logs(limit=limit, level=levelno)}


@router.websocket("/logs")
async def logs_stream(websocket: WebSocket):
    await websocket.accept()
    handler: InMemoryLogHandler = getattr(websocket.app.state, "log_handler", None)
    if handler is None:
        handler = setup_in_memory_logging(
            "system_wizyjny", level=logging.INFO, maxlen=100
        )
        websocket.app.state.log_handler = handler

    queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    class WSLogHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                queue.put_nowait(record)
            except asyncio.QueueFull:
                pass

    ws_handler = WSLogHandler()
    ws_handler.setLevel(logging.DEBUG)
    logger = logging.getLogger("system_wizyjny")
    logger.addHandler(ws_handler)

    async def recv_until_disconnect() -> None:
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass

    recv_task: Optional[asyncio.Task] = None
    queue_task: Optional[asyncio.Task] = None
    stop_task: Optional[asyncio.Task] = None

    try:
        recv_task = asyncio.create_task(recv_until_disconnect())
        queue_task = asyncio.create_task(queue.get())
        stop_task = asyncio.create_task(shutdown_event.wait())

        while True:
            done, _ = await asyncio.wait(
                {recv_task, queue_task, stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if recv_task in done or stop_task in done:
                break

            if queue_task in done:
                record = queue_task.result()
                message = handler._serialize(record)
                await websocket.send_json(message)
                queue_task = asyncio.create_task(queue.get())
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - need real exception info
        logger.error("WebSocket error: %s", exc)
    finally:
        logger.removeHandler(ws_handler)
        for task in (recv_task, queue_task, stop_task):
            if isinstance(task, asyncio.Task):
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        with suppress(Exception):
            await websocket.close(code=1001)
