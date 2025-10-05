import snap7
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from .wizja import wizja_still

DB_NUMBER = 1  # Numer bloku danych, który będziemy monitorować

# DB1.DBX0.0 – start analizy (PLC ustawia na 1, Python zeruje po analizie)
# DB1.DBX0.1 – wynik analizy (Python ustawia 0/1)
# DB1.DBX0.2 – analiza zakończona (Python ustawia na 1 po analizie)
# DB1.DBX0.3 – error RPi

# DB1.DBX1.0 - Przyciski on/off (ten co zielony na linii)

# pozostale przyciski na linii:
# DB1.DBX1.1 - czerwony
# DB1.DBX1.2 - zółty (z lampka DB1.DBX0.7)

# DB1.DBX0.6 - on/off system wizyjny

# lampki:
# DB1.DBX1.3 - switch (status)
# DB1.DBX1.4 - zielona
# DB1.DBX1.5 - czerwona
# DB1.DBX1.6 - pomarańczowa
# DB1.DBX1.7 - biała
# DB1.DBX0.7 - zółta (przycisk DB1.DBX1.2 z lampką)

# Zliczanie elementow:
# DB1.DBX2.0 - dobre
# DB1.DBX4.0 - zle
# suma elementów (do obliczenia)

# DB1.DBX6.0 - Status (np. ready, running ip)

# DB1.DBX8.0 - predkosc (odczyt + zapis)

logger = logging.getLogger("system_wizyjny")


@dataclass
class LiniaDataStore:
    """
    A class to store and manage the PLC data.
    """

    analyze: int = 0
    result: int = 0
    finished: int = 0
    error: int = 0

    on_off: int = 0
    red_button: int = 0
    yellow_button: int = 0

    system_wizyjny_on_off: int = 0

    switch_status: int = 0
    green_light: int = 0
    red_light: int = 0
    orange_light: int = 0
    yellow_button_light: int = 0
    white_light: int = 0

    good_count: int = 0
    bad_count: int = 0

    status: int = 0

    speed: int = 0  # 0 - 100

    _last_connected: datetime = None
    _subscribers: list = None

    @property
    def is_connected(self) -> bool:
        if self._last_connected is None:
            return False
        return (datetime.now() - self._last_connected).total_seconds() <= 2

    def __post_init__(self):
        self._subscribers = []

    def set_data(self, **kwargs):
        for k, v in kwargs.items():
            if k not in (
                "on_off",
                "red_button",
                "yellow_button",
                "speed",
                "system_wizyjny_on_off",
            ):
                continue
            if hasattr(self, k):
                setattr(self, k, v)
                # test
                if k == "on_off" and v == 1:
                    self.green_light = 1 - self.green_light
        for q in self._subscribers:
            try:
                q.put_nowait(self)
            except asyncio.QueueFull:
                pass  # If the queue is full, we skip notifying this subscriber

    def dict(self):
        exclude_fields = []
        extra_fields = ["is_connected"]
        return {
            k: v
            for (k, v) in self.__dict__.items()
            if (
                (v is not None)
                and (not k.startswith("_"))
                and (k not in exclude_fields)
            )
        } | {k: getattr(self, k) for k in extra_fields}

    def from_bytes(self, from_bytes: bytes):
        self.analyze = from_bytes[0] & 0x01
        self.result = (from_bytes[0] >> 1) & 0x01
        self.finished = (from_bytes[0] >> 2) & 0x01
        self.error = (from_bytes[0] >> 3) & 0x01

        self.system_wizyjny_on_off = (from_bytes[0] >> 6) & 0x01

        self.on_off = from_bytes[1] & 0x01
        self.red_button = (from_bytes[1] >> 1) & 0x01
        self.yellow_button = (from_bytes[1] >> 2) & 0x01
        self.switch_status = (from_bytes[1] >> 3) & 0x01
        self.green_light = (from_bytes[1] >> 4) & 0x01
        self.red_light = (from_bytes[1] >> 5) & 0x01
        self.orange_light = (from_bytes[1] >> 6) & 0x01
        self.yellow_button_light = (from_bytes[0] >> 7) & 0x01
        self.white_light = (from_bytes[1] >> 7) & 0x01

        self.good_count = int.from_bytes(from_bytes[2:4], byteorder="big")
        self.bad_count = int.from_bytes(from_bytes[4:6], byteorder="big")

        self.status = int.from_bytes(from_bytes[6:8], byteorder="big")

        self.speed = int.from_bytes(from_bytes[8:10], byteorder="big")

    def to_bytes(self):
        return (
            bytearray(
                [
                    (self.analyze << 0)
                    | (self.result << 1)
                    | (self.finished << 2)
                    | (self.error << 3)
                    | (self.system_wizyjny_on_off << 6)
                    | (self.yellow_button_light << 7),
                    (self.on_off << 0)
                    | (self.red_button << 1)
                    | (self.yellow_button << 2)
                    | (self.switch_status << 3)
                    | (self.green_light << 4)
                    | (self.red_light << 5)
                    | (self.orange_light << 6)
                    | (self.white_light << 7),
                ]
            )
            + self.good_count.to_bytes(2, byteorder="big")
            + self.bad_count.to_bytes(2, byteorder="big")
            + self.status.to_bytes(2, byteorder="big")
            + self.speed.to_bytes(2, byteorder="big")
        )

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)


class LiniaConnection:
    """
    A class to talk with linia S7 PLC.
    """

    def __init__(self, ip_address, data_store, rack=0, slot=1, port=102):
        self.ip_address = ip_address
        self.rack = rack
        self.slot = slot
        self.port = port
        self.client = snap7.client.Client()
        self.data_store = data_store

    def connect(self):
        if self.client.get_connected():
            return True
        try:
            self.client.connect(self.ip_address, self.rack, self.slot, self.port)
        except Exception as e:
            logger.error(f"Błąd połączenia z PLC: {e}")
            return False
        self.data_store._last_connected = datetime.now()
        logger.info("Połączono z PLC.")
        return True

    # analyze = 0
    # result = 0
    # finished = 0
    # error = 0

    async def read(self):
        """
        Reads the data from the PLC.
        """
        if not self.client.get_connected():
            self.connect()  # Ensure connection is established
        try:
            data = self.client.db_read(DB_NUMBER, 0, 10)
        except Exception as e:
            logger.error(f"Błąd odczytu danych z PLC: {e}")
            return False
        self.data_store.from_bytes(bytes_values=data)
        self.data_store._last_connected = datetime.now()
        return True

    async def write(self):
        """
        Writes the result and finished back to the PLC.
        """
        new_bytes = self.data_store.to_bytes()
        if not self.client.get_connected():
            self.connect()  # Ensure connection is established

        self.client.db_write(DB_NUMBER, 0, new_bytes)
        self.data_store._last_connected = datetime.now()
        return True


def _should_detect_red_circle(result: dict) -> bool:
    try:
        return bool(
            result
            and result.get("circles")
            and result.get("circles")[0]["color"] == "czerwony"
        )
    except Exception:
        return False


async def monitor_and_analyze(data_store, linia):

    while True:
        try:
            if await linia.read() and data_store.analyze:
                logger.info("Start analizy!")
                try:
                    # Tutaj można dodać kod do analizy danych
                    wizja_result = wizja_still()
                    logger.info(f"Wynik analizy: {wizja_result}")
                    if _should_detect_red_circle(wizja_result):
                        logger.info("Wykryto czerwone koło, zapisuję wynik jako 1...")
                        data_store.result = 1
                    else:
                        logger.info(
                            "Nie wykryto czerwonego koła, zapisuję wynik jako 0..."
                        )
                        data_store.result = 0

                    data_store.finished = 1
                    data_store.analyze = 0
                    data_store.error = 0
                except Exception as e:
                    logger.exception(f"Błąd podczas analizy: {e}")
                    data_store.error = 1

                await linia.write()
                logger.info("Analiza zakończona, wynik zapisany.")
        except Exception as e:
            logger.exception(str(e))

        await asyncio.sleep(0.2)


if __name__ == "__main__":
    data_store = LiniaDataStore()
    asyncio.run(
        monitor_and_analyze("127.0.0.1", data_store=data_store)
    )  # Podaj IP swojego PLC
