import snap7
import asyncio
import logging
from dataclasses import dataclass

from .wizja import wizja_still

DB_NUMBER = 1  # Numer bloku danych, który będziemy monitorować

# DB1.DBX0.0 – start analizy (PLC ustawia na 1, Python zeruje po analizie)
# DB1.DBX0.1 – wynik analizy (Python ustawia 0/1)
# DB1.DBX0.2 – analiza zakończona (Python ustawia na 1 po analizie)
# DB1.DBX0.3 – error RPi

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

    def from_byte(self, byte):
        self.analyze = byte & 0x01
        self.result = (byte >> 1) & 0x01
        self.finished = (byte >> 2) & 0x01
        self.error = (byte >> 3) & 0x01

    def to_byte(self):
        return (
            (self.analyze << 0)
            | (self.result << 1)
            | (self.finished << 2)
            | (self.error << 3)
        )


class LiniaCnnection:
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
        logger.info("Połączono z PLC.")
        return True

    # analyze = 0
    # result = 0
    # finished = 0
    # error = 0

    def read(self):
        """
        Reads the data from the PLC.
        """
        if not self.client.get_connected():
            self.connect()  # Ensure connection is established
        try:
            data = self.client.db_read(DB_NUMBER, 0, 1)
        except Exception as e:
            logger.error(f"Błąd odczytu danych z PLC: {e}")
            return False
        byte_value = data[0]
        self.data_store.from_byte(byte_value)
        return True

    def write(self):
        """
        Writes the result and finished back to the PLC.
        """
        new_byte = self.data_store.to_byte()
        if not self.client.get_connected():
            self.connect()  # Ensure connection is established

        self.client.db_write(DB_NUMBER, 0, bytearray([new_byte]))


def _should_detect_red_circle(result: dict) -> bool:
    try:
        return bool(
            result
            and result.get("circles")
            and result.get("circles")[0]["color"] == "czerwony"
        )
    except Exception:
        return False


async def monitor_and_analyze(ip_address, data_store, rack=0, slot=1, port=102):
    linia = LiniaCnnection(ip_address, data_store, rack, slot, port)

    while True:
        try:
            if linia.read() and data_store.analyze:
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

                linia.write()
                logger.info("Analiza zakończona, wynik zapisany.")
        except Exception as e:
            logger.exception(str(e))

        await asyncio.sleep(0.2)


if __name__ == "__main__":
    data_store = LiniaDataStore()
    asyncio.run(
        monitor_and_analyze("127.0.0.1", data_store=data_store)
    )  # Podaj IP swojego PLC
