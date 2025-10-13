import asyncio
import os
import logging
from dotenv import load_dotenv

from src.plc_connection import LiniaConnection, LiniaDataStore
from src.camera import Camera

logger = logging.getLogger("system_wizyjny")
logger.setLevel(logging.DEBUG)

data_store = LiniaDataStore()
shutdown_event: asyncio.Event = asyncio.Event()

load_dotenv()

ip_address = os.getenv("PLC_IP_ADDRESS", "192.168.0.1")
rack = int(os.getenv("PLC_RACK", "0"))
slot = int(os.getenv("PLC_SLOT", "1"))
port = int(os.getenv("PLC_PORT", "102"))

linia = LiniaConnection(
    ip_address=ip_address,
    data_store=data_store,
    rack=rack,
    slot=slot,
    port=port,
)

try:
    camera = Camera()
except:
    camera = None
    logger.error("Błąd inicjacji kamery")

__all__ = [
    "camera",
    "data_store",
    "linia",
    "shutdown_event",
]
