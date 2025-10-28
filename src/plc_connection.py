import asyncio
import logging

from .leds import *

led_ctrl = WS2812Flash()

from .wizja import wizja_still
from .plc_lib import PLCData, PLCBoolField, PLCWordField, PLCRealField, PLCConnection

DB_NUMBER = 1  # Numer bloku danych, który będziemy monitorować

# DB1.DBX0.0 – start analizy (PLC ustawia na 1, Python zeruje po analizie)
# DB1.DBX0.1 – wynik analizy (Python ustawia 0/1)
# DB1.DBX0.2 – analiza zakończona (Python ustawia na 1 po analizie)
# DB1.DBX0.3 – error RPi

# DB1.DBX0.4 - on/off system wizyjny
# DB1.DBX0.5 - Przycisk on/off (zielony przycisk)

# DB1.DBX0.6 - czerwony przycisk

# lampki:
# DB1.DBX0.7 - switch (status)
# DB1.DBX1.0 - zielona
# DB1.DBX1.1 - czerwona
# DB1.DBX1.2 - pomarańczowa
# DB1.DBX1.3 - biała
# DB1.DBX1.4 - zółta (przycisk DB1.DBX1.5 z lampką)

# DB1.DBX1.5 - zółty przycisk (z lampką DB1.DBX1.5)

# Zliczanie elementow:
# DB1.DBX2.0 - dobre 2B
# DB1.DBX4.0 - zle 2B
# DB1.DBX6.0 - suma elementów (do obliczenia)

# DB1.DBX8.0 - predkosc (Real) (odczyt + zapis) 4B od -100 do 100

# DB1.DBX12.0 - Status (Int) 2B

logger = logging.getLogger("system_wizyjny")
logger.setLevel(logging.DEBUG)


class LiniaDataStore(PLCData):
    """
    DataStore describing DB1 layout for the production line PLC.
    """

    analyze = PLCBoolField(0, 0, settable=True)
    result = PLCBoolField(0, 1)
    finished = PLCBoolField(0, 2)
    error = PLCBoolField(0, 3)

    system_wizyjny_on_off = PLCBoolField(0, 4, settable=True)
    on_off = PLCBoolField(0, 5, settable=True)
    red_button = PLCBoolField(0, 6, settable=True)
    switch_status = PLCBoolField(0, 7)

    green_light = PLCBoolField(1, 0)
    red_light = PLCBoolField(1, 1)
    orange_light = PLCBoolField(1, 2)
    white_light = PLCBoolField(1, 3)
    yellow_button_light = PLCBoolField(1, 4)
    yellow_button = PLCBoolField(1, 5, settable=True)

    good_count = PLCWordField(2)
    bad_count = PLCWordField(4)

    speed = PLCRealField(8, settable=True)
    status = PLCWordField(12)

    klocek_w_podajniku = PLCBoolField(14, 0)

    tryb_auto = PLCBoolField(14, 1, settable=True)

    def notify_subscribers(self):
        super().notify_subscribers()
        if self.system_wizyjny_on_off:
            led_ctrl.flash_on()
        else:
            led_ctrl.flash_off()


class LiniaConnection(PLCConnection):
    pass


def _should_detect_red_circle(result: dict) -> bool:
    try:
        return bool(
            result
            and result.get("circles")
            and result.get("circles")[0]["color"] == "czerwony"
        )
    except Exception:
        return False


async def monitor_and_analyze(data_store, linia, camera):
    while True:
        try:
            await linia.read()
            if data_store.analyze:
                logger.info("Start analizy!")
                try:
                    # Tutaj można dodać kod do analizy danych
                    wizja_result = wizja_still(camera=camera)
                    logger.info(f"Wynik analizy: {wizja_result}")
                    if _should_detect_red_circle(wizja_result):
                        logger.info("Wykryto czerwone koło, zapisuję wynik jako 1...")
                        data_store.result = 1
                    else:
                        logger.info(
                            "Nie wykryto czerwonego koła, zapisuję wynik jako 0..."
                        )
                        data_store.result = 0

                    data_store.error = 0
                    data_store.finished = 1
                except Exception as e:
                    logger.exception(f"Błąd podczas analizy: {e}")
                    data_store.error = 1

                data_store.set_data(analyze=0)

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
