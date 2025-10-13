import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.logging_utils import setup_in_memory_logging
from src.plc_connection import monitor_and_analyze
from src.state import camera, data_store, linia, shutdown_event

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure global state and background tasks when the app starts."""
    shutdown_event.clear()
    handler = setup_in_memory_logging("system_wizyjny", level=logging.INFO, maxlen=100)
    app.state.log_handler = handler
    asyncio.create_task(monitor_and_analyze(data_store=data_store, linia=linia, camera=camera))
    try:
        yield
    finally:
        shutdown_event.set()
        if camera is not None:
            camera.stop()
