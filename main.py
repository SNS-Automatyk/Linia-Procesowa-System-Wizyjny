from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager, suppress
import asyncio
import logging
from typing import Optional
import json
import os
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import mimetypes

from src.plc_connection import monitor_and_analyze, LiniaDataStore, LiniaConnection
from src.logging_utils import setup_in_memory_logging, InMemoryLogHandler
from src.camera import Camera

data_store = LiniaDataStore()
shutdown_event: asyncio.Event = asyncio.Event()

ip_address = os.getenv("PLC_IP_ADDRESS", "192.168.0.1")
rack = int(os.getenv("PLC_RACK", "0"))
slot = int(os.getenv("PLC_SLOT", "1"))
port = int(os.getenv("PLC_PORT", "102"))

linia = LiniaConnection(
    ip_address=ip_address, data_store=data_store, rack=rack, slot=slot, port=port
)
camera = Camera()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure in-memory logging once app starts
    handler = setup_in_memory_logging("system_wizyjny", level=logging.INFO, maxlen=100)
    app.state.log_handler = handler
    asyncio.create_task(monitor_and_analyze(data_store=data_store, linia=linia))
    try:
        yield
    finally:
        # Signal all handlers to stop promptly
        shutdown_event.set()
        camera.stop()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api")
def root():
    return {
        "status": "success",
        "data": data_store.dict(),
    }


@app.put("/api")
async def root_put(data: dict):
    """
    Update the PLC data store with provided values.
    Accepts JSON body with any of the fields: analyze, result, finished, error.
    """
    data_store.set_data(**data.get("data", {}))
    try:
        await linia.write()  # Write updated data to PLC
    except Exception as e:
        logger = logging.getLogger("system_wizyjny")
        logger.error(f"Błąd podczas zapisu do PLC: {e}")
        return {"status": "error", "message": str(e)}
    return {"status": "success"}


@app.websocket("/api")
async def root_websocket(websocket: WebSocket):
    await websocket.accept()
    q = data_store.subscribe()

    data = data_store.dict()
    await websocket.send_json({"status": "init", "data": data})  # Send initial data

    async def _recv_until_disconnect() -> None:
        try:
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                data_store.set_data(**data.get("data", {}))
                try:
                    await linia.write()  # Write updated data to PLC
                except Exception as e:
                    logger = logging.getLogger("system_wizyjny")
                    logger.error(f"Błąd podczas zapisu do PLC: {e}")
        except WebSocketDisconnect:
            pass

    recv_task: asyncio.Task | None = None
    q_task: asyncio.Task | None = None
    stop_task: asyncio.Task | None = None
    try:
        recv_task = asyncio.create_task(_recv_until_disconnect())
        q_task = asyncio.create_task(q.get())
        stop_task = asyncio.create_task(shutdown_event.wait())
        while True:
            done, pending = await asyncio.wait(
                {recv_task, q_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
            )

            # If client disconnected, stop
            if recv_task in done:
                break

            # If server is shutting down, stop
            if stop_task in done:
                break

            # Otherwise, we have data to send
            if q_task in done:
                data = q_task.result()
                await websocket.send_json(
                    {
                        "status": "update",
                        "data": data.dict(),
                    }
                )
                # re-arm queue waiter
                q_task = asyncio.create_task(q.get())
    except WebSocketDisconnect:
        # Client disconnected
        pass
    except asyncio.CancelledError:
        # Server shutdown / task cancellation
        raise
    except Exception as e:
        logger = logging.getLogger("system_wizyjny")
        logger.error(f"WebSocket error: {e}")
    finally:
        data_store.unsubscribe(q)
        if recv_task is not None:
            recv_task.cancel()
            with suppress(asyncio.CancelledError):
                await recv_task
        if q_task is not None:
            q_task.cancel()
            with suppress(asyncio.CancelledError):
                await q_task
        if stop_task is not None:
            stop_task.cancel()
            with suppress(asyncio.CancelledError):
                await stop_task
        with suppress(Exception):
            await websocket.close()


@app.get("/logs")
def get_logs(
    limit: Optional[int] = Query(default=200, ge=1, le=2000),
    level: Optional[str] = Query(default=None),
):
    """Return recent logs captured from the system_wizyjny logger.

    Query params:
    - limit: max number of entries
    - level: optional minimum level name (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    """
    handler: InMemoryLogHandler = getattr(app.state, "log_handler", None)
    if handler is None:
        # Safety: if not configured yet, set it up now
        handler = setup_in_memory_logging(
            "system_wizyjny", level=logging.INFO, maxlen=100
        )
        app.state.log_handler = handler

    levelno = None
    if level:
        level_upper = level.upper()
        if hasattr(logging, level_upper):
            levelno = getattr(logging, level_upper)
        else:
            return {"error": f"Unknown level: {level}"}

    return {"logs": handler.get_logs(limit=limit, level=levelno)}


@app.websocket("/logs")
async def logs_websocket(websocket: WebSocket):
    await websocket.accept()
    handler: InMemoryLogHandler = getattr(app.state, "log_handler", None)
    if handler is None:
        # Safety: if not configured yet, set it up now
        handler = setup_in_memory_logging(
            "system_wizyjny", level=logging.INFO, maxlen=100
        )
        app.state.log_handler = handler

    q: asyncio.Queue = asyncio.Queue(maxsize=100)

    class WSLogHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                q.put_nowait(record)
            except asyncio.QueueFull:
                pass  # Drop log if queue is full

    ws_handler = WSLogHandler()
    ws_handler.setLevel(logging.DEBUG)
    logger = logging.getLogger("system_wizyjny")
    logger.addHandler(ws_handler)

    try:

        async def _recv_until_disconnect() -> None:
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                pass

        recv_task: asyncio.Task | None = asyncio.create_task(_recv_until_disconnect())
        q_task: asyncio.Task | None = asyncio.create_task(q.get())
        stop_task: asyncio.Task | None = asyncio.create_task(shutdown_event.wait())
        while True:
            done, pending = await asyncio.wait(
                {recv_task, q_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
            )

            if recv_task in done or stop_task in done:
                break

            if q_task in done:
                record = q_task.result()
                message = handler._serialize(record)
                await websocket.send_json(message)
                q_task = asyncio.create_task(q.get())
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.removeHandler(ws_handler)
        # cancel pending tasks
        for t in (
            locals().get("recv_task"),
            locals().get("q_task"),
            locals().get("stop_task"),
        ):
            if isinstance(t, asyncio.Task):
                t.cancel()
                with suppress(asyncio.CancelledError):
                    await t
        with suppress(Exception):
            await websocket.close(code=1001)


@app.get("/camera")
async def camera_stream():
    return StreamingResponse(
        camera.mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# Statyki Vue
DIST = os.environ.get(
    "DIST_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "panel-sterowania/dist"),
)
app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

# Ensure correct content type for web manifest files
mimetypes.add_type("application/manifest+json", ".webmanifest")

# Expose additional top-level static files emitted by Vite public/
app.mount("/favicon.ico", StaticFiles(directory=DIST), name="favicon")
app.mount("/apple-touch-icon.png", StaticFiles(directory=DIST), name="apple-touch-icon")
app.mount(
    "/android-chrome-192x192.png",
    StaticFiles(directory=DIST),
    name="android-chrome-192x192",
)
app.mount(
    "/android-chrome-384x384.png",
    StaticFiles(directory=DIST),
    name="android-chrome-384x384",
)
app.mount("/browserconfig.xml", StaticFiles(directory=DIST), name="browserconfig")
app.mount("/favicon-16x16.png", StaticFiles(directory=DIST), name="favicon-16x16")
app.mount("/favicon-32x32.png", StaticFiles(directory=DIST), name="favicon-32x32")
app.mount("/mstile-150x150.png", StaticFiles(directory=DIST), name="mstile-150x150")
app.mount(
    "/safari-pinned-tab.svg", StaticFiles(directory=DIST), name="safari-pinned-tab"
)
app.mount("/site.webmanifest", StaticFiles(directory=DIST), name="site-webmanifest")


# SPA fallback: wszystko co nie /api i nie /ws zwraca index.html
@app.get("/{full_path:path}")
def spa(full_path: str):
    return FileResponse(os.path.join(DIST, "index.html"))


def main():
    print("Hello from system-wizyjny!")


if __name__ == "__main__":
    main()
