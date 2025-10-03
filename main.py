from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
from dataclasses import asdict
from typing import Optional

from src.plc_connection import monitor_and_analyze, LiniaDataStore
from src.logging_utils import setup_in_memory_logging, InMemoryLogHandler

data_store = LiniaDataStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure in-memory logging once app starts
    handler = setup_in_memory_logging("system_wizyjny", level=logging.INFO, maxlen=100)
    app.state.log_handler = handler
    # asyncio.create_task(monitor_and_analyze("127.0.0.1", data_store=data_store))
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return asdict(data_store)


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


def main():
    print("Hello from system-wizyjny!")


if __name__ == "__main__":
    main()
