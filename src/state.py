import asyncio
import os

from src.plc_connection import LiniaConnection, LiniaDataStore
from src.camera import Camera


data_store = LiniaDataStore()
shutdown_event: asyncio.Event = asyncio.Event()

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

camera = Camera()

__all__ = [
    "camera",
    "data_store",
    "linia",
    "shutdown_event",
]
