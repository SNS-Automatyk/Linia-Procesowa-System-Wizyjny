import asyncio
import snap7
import logging
from collections import OrderedDict
from datetime import datetime
import struct
from datetime import datetime
import socket
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("system_wizyjny")


class PLCField:
    """
    Base descriptor representing a single PLC variable.
    """

    def __init__(
        self, byte_offset: int, *, size: int, default=0, settable: bool = False
    ):
        self.byte_offset = byte_offset
        self.size = size
        self.default = default
        self.settable = settable
        self.name: str | None = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance._values.get(self.name, self.default)

    def __set__(self, instance, value):
        instance._values[self.name] = self.coerce(value)

    def coerce(self, value):
        return value

    def read(self, data: bytes, current):
        return current

    def write(self, buffer: bytearray, value):
        raise NotImplementedError


class PLCBoolField(PLCField):
    """
    Field representing a boolean stored as a single bit.
    """

    def __init__(
        self,
        byte_offset: int,
        bit_offset: int,
        *,
        default: int = 0,
        settable: bool = False,
    ):
        super().__init__(
            byte_offset, size=1, default=int(bool(default)), settable=settable
        )
        self.bit_offset = bit_offset

    def coerce(self, value):
        return 1 if bool(value) else 0

    def read(self, data: bytes, current):
        if len(data) <= self.byte_offset:
            return current
        byte_value = data[self.byte_offset]
        return (byte_value >> self.bit_offset) & 0x01

    def write(self, buffer: bytearray, value):
        value = self.coerce(value)
        mask = 1 << self.bit_offset
        if value:
            buffer[self.byte_offset] |= mask
        else:
            buffer[self.byte_offset] &= (~mask) & 0xFF


class PLCWordField(PLCField):
    """
    Field representing a 16-bit integer value (WORD).
    """

    def __init__(
        self,
        byte_offset: int,
        *,
        default: int = 0,
        signed: bool = False,
        settable: bool = False,
    ):
        super().__init__(byte_offset, size=2, default=int(default), settable=settable)
        self.signed = signed

    def _clamp(self, value: int) -> int:
        value = int(value)
        if self.signed:
            return max(min(value, 32767), -32768)
        return max(min(value, 0xFFFF), 0)

    def coerce(self, value):
        return self._clamp(value)

    def read(self, data: bytes, current):
        slice_ = data[self.byte_offset : self.byte_offset + self.size]
        if len(slice_) < self.size:
            return current
        return int.from_bytes(slice_, byteorder="big", signed=self.signed)

    def write(self, buffer: bytearray, value):
        value = self.coerce(value)
        buffer[self.byte_offset : self.byte_offset + self.size] = value.to_bytes(
            self.size, byteorder="big", signed=self.signed
        )


class PLCRealField(PLCField):
    """
    Field representing a 32-bit IEEE-754 floating point value (REAL).
    """

    def __init__(
        self, byte_offset: int, *, default: float = 0.0, settable: bool = False
    ):
        super().__init__(byte_offset, size=4, default=float(default), settable=settable)

    def coerce(self, value):
        return float(value)

    def read(self, data: bytes, current):
        slice_ = data[self.byte_offset : self.byte_offset + self.size]
        if len(slice_) < self.size:
            return current
        try:
            return struct.unpack(">f", slice_)[0]
        except struct.error:
            return current

    def write(self, buffer: bytearray, value):
        buffer[self.byte_offset : self.byte_offset + self.size] = struct.pack(
            ">f", float(value)
        )


class PLCDataMeta(type):
    """
    Metaclass collecting PLC field descriptors in definition order.
    """

    def __new__(mcls, name, bases, namespace):
        fields = OrderedDict()

        for base in bases:
            base_fields = getattr(base, "_fields", None)
            if base_fields:
                fields.update(base_fields)

        for attr_name, attr_value in list(namespace.items()):
            if isinstance(attr_value, PLCField):
                attr_value.name = attr_name
                fields[attr_name] = attr_value

        namespace["_fields"] = fields
        return super().__new__(mcls, name, bases, namespace)


class PLCData(metaclass=PLCDataMeta):
    """
    Base class handling automatic serialization/deserialization for PLC fields.
    """

    def __init__(self, **initial_values):
        self._values: Dict[str, object] = {
            name: field.coerce(field.default) for name, field in self._fields.items()
        }
        self._subscribers: List[asyncio.Queue] = []

        for key, value in initial_values.items():
            if key in self._fields:
                setattr(self, key, value)

    IS_CONNECTED_TIMEOUT = 2  # seconds

    _last_connected: Optional[datetime] = None

    @property
    def is_connected(self) -> bool:
        if self._last_connected is None:
            return False
        return (
            datetime.now() - self._last_connected
        ).total_seconds() <= self.IS_CONNECTED_TIMEOUT

    def last_connected_setter(self, value):
        self.old_is_connected = self.is_connected
        self._last_connected = value
        if self.old_is_connected != self.is_connected:
            self.notify_subscribers()

        # check connection status after timeout
        self._last_connected_timeout = asyncio.get_event_loop().call_later(
            self.IS_CONNECTED_TIMEOUT, self._on_connection_timeout
        )

    last_connected = property(lambda self: self._last_connected, last_connected_setter)

    def _on_connection_timeout(self):
        if self.old_is_connected != self.is_connected:
            self.notify_subscribers()
            self.old_is_connected = self.is_connected

    @classmethod
    def buffer_size(cls) -> int:
        if not cls._fields:
            return 0
        return max(field.byte_offset + field.size for field in cls._fields.values())

    def set_data(self, **kwargs):
        processed = False
        for key, value in kwargs.items():
            field = self._fields.get(key)
            if field is None or not field.settable:
                continue
            if getattr(self, key) == field.coerce(value):
                continue
            setattr(self, key, value)
            processed = True

        if processed:
            self.notify_subscribers()

    def dict(self):
        data = {name: getattr(self, name) for name in self._fields}
        data["is_connected"] = self.is_connected
        return data

    def from_bytes(self, raw: bytes):
        for name, field in self._fields.items():
            current = self._values.get(name, field.default)
            self._values[name] = field.read(raw, current)
        self.notify_subscribers()

    def to_bytes(self) -> bytes:
        buffer = bytearray(self.buffer_size())
        for name, field in self._fields.items():
            field.write(buffer, getattr(self, name))
        return bytes(buffer)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    def notify_subscribers(self):
        for q in self._subscribers:
            try:
                q.put_nowait(self)
            except asyncio.QueueFull:
                pass


class PLCConnection:
    """
    A class to talk with linia S7 PLC.
    """

    def __init__(
        self,
        ip_address,
        data_store,
        db_numer=1,
        rack=0,
        slot=1,
        port=102,
        connect_timeout: float = 1.5,
    ):
        self.ip_address = ip_address
        self.db_numer = db_numer
        self.rack = rack
        self.slot = slot
        self.port = port
        self.connect_timeout = float(connect_timeout)
        self.client = snap7.client.Client()
        self.data_store = data_store

    def notify_subscribers(self):
        """Forward notifications to the underlying data store subscribers."""
        try:
            self.data_store.notify_subscribers()
        except Exception:
            # Keep defensive; notification should never block connection flow
            pass

    def connect(self):
        """
        Ensure client is connected. Returns True when connected, False otherwise.
        Uses a preflight TCP connect with timeout to avoid indefinite blocking.
        """
        try:
            if self.client.get_connected():
                return True
        except Exception as e:
            # Defensive: some native failures may bubble up here
            logger.error(f"Błąd podczas sprawdzania stanu połączenia PLC: {e}")
            return False

        # Preflight TCP connection with timeout to avoid hanging in snap7.connect
        try:
            with socket.create_connection(
                (self.ip_address, self.port), timeout=self.connect_timeout
            ) as s:
                # Successful low-level TCP connect; proceed with snap7 handshake
                pass
        except Exception as e:
            # logger.error(
            #     f"Timeout/błąd podczas nawiązywania połączenia TCP z PLC {self.ip_address}:{self.port} w {self.connect_timeout:.1f}s: {e}"
            # )
            return False

        try:
            self.client.connect(self.ip_address, self.rack, self.slot, self.port)
        except Exception as e:
            logger.error(f"Błąd połączenia z PLC: {e}")
            return False

        self.data_store.last_connected = datetime.now()
        logger.info("Połączono z PLC.")
        return True

    async def read(self):
        """
        Reads the data from the PLC.
        """
        # Establish connection if needed; avoid db_read on disconnected client
        try:
            connected = self.client.get_connected()
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania połączenia PLC: {e}")
            connected = False

        if not connected:
            if not self.connect():
                self.connect()
                # Not connected, skip read this cycle
                return False
        try:
            byte_amount = self.data_store.buffer_size()
            data = self.client.db_read(self.db_numer, 0, byte_amount)
        except Exception as e:
            logger.error(f"Błąd odczytu danych z PLC: {e}")
            return False

        self.data_store.from_bytes(data)
        self.data_store.last_connected = datetime.now()

        return True

    async def write(self):
        """
        Writes the result and finished back to the PLC.
        """
        new_bytes = self.data_store.to_bytes()
        # Establish connection if needed; avoid db_write on disconnected client
        try:
            connected = self.client.get_connected()
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania połączenia PLC: {e}")
            connected = False
            return False

        if not connected:
            if not self.connect():
                return False

        try:
            self.client.db_write(self.db_numer, 0, new_bytes)
        except Exception as e:
            logger.error(f"Błąd zapisu danych do PLC: {e}")
            return False

        self.data_store.last_connected = datetime.now()

        return True
