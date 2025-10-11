import asyncio
import json
import logging
from contextlib import suppress
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.state import data_store, linia, shutdown_event


router = APIRouter()


@router.get("/api")
def read_data():
    return {
        "status": "success",
        "data": data_store.dict(),
    }


@router.put("/api")
async def update_data(payload: dict):
    """Update PLC data with incoming values."""
    data_store.set_data(**payload.get("data", {}))
    try:
        await linia.write()
    except Exception as exc:  # noqa: BLE001 - need real exception info
        logger = logging.getLogger("system_wizyjny")
        logger.error("Błąd podczas zapisu do PLC: %s", exc)
        return {"status": "error", "message": str(exc)}
    return {"status": "success"}


@router.websocket("/api")
async def update_data_stream(websocket: WebSocket):
    await websocket.accept()
    queue = data_store.subscribe()
    await websocket.send_json({"status": "init", "data": data_store.dict()})

    async def recv_until_disconnect() -> None:
        try:
            while True:
                message = await websocket.receive_text()
                payload = json.loads(message)
                data_store.set_data(**payload.get("data", {}))
                try:
                    await linia.write()
                except Exception as exc:  # noqa: BLE001 - need real exception info
                    logger = logging.getLogger("system_wizyjny")
                    logger.error("Błąd podczas zapisu do PLC: %s", exc)
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
            done, pending = await asyncio.wait(
                {recv_task, queue_task, stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if recv_task in done or stop_task in done:
                break

            if queue_task in done:
                item = queue_task.result()
                await websocket.send_json({"status": "update", "data": item.dict()})
                queue_task = asyncio.create_task(queue.get())
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - need real exception info
        logger = logging.getLogger("system_wizyjny")
        logger.error("WebSocket error: %s", exc)
    finally:
        data_store.unsubscribe(queue)
        for task in (recv_task, queue_task, stop_task):
            if isinstance(task, asyncio.Task):
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        with suppress(Exception):
            await websocket.close()
