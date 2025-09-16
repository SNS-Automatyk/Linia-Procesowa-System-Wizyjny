import snap7
import time
from .wizja import wizja_still

DB_NUMBER = 1  # Numer bloku danych, który będziemy monitorować

# DB1.DBX0.0 – start analizy (PLC ustawia na 1, Python zeruje po analizie)
# DB1.DBX0.1 – wynik analizy (Python ustawia 0/1)
# DB1.DBX0.2 – analiza zakończona (Python ustawia na 1 po analizie)
# DB1.DBX0.3 – error RPi


class LiniaCnnection:
    """
    A class to talk with linia S7 PLC.
    """

    def __init__(self, ip_address, rack=0, slot=1, port=102):
        self.ip_address = ip_address
        self.rack = rack
        self.slot = slot
        self.port = port
        self.client = snap7.client.Client()
        self.connect()

    def connect(self):
        try:
            self.client.connect(self.ip_address, self.rack, self.slot, self.port)
        except Exception as e:
            print(f"Błąd połączenia z PLC: {e}")
            return False
        print("Połączono z PLC.")
        return True

    analyze = 0
    result = 0
    finished = 0
    error = 0

    def read(self):
        """
        Reads the data from the PLC.
        """
        if not self.client.get_connected():
            self.connect()  # Ensure connection is established
        try:
            data = self.client.db_read(DB_NUMBER, 0, 1)
        except Exception as e:
            print(f"Błąd odczytu danych z PLC: {e}")
            return False
        self.analyze = data[0] & 0x01
        self.result = (data[0] >> 1) & 0x01
        self.finished = (data[0] >> 2) & 0x01
        self.error = (data[0] >> 3) & 0x01
        return True

    def write(self):
        """
        Writes the result and finished back to the PLC.
        """
        new_byte = (
            (self.analyze << 0)
            | (self.result << 1)
            | (self.finished << 2)
            | (self.error << 3)
        )  # Bit 0 = 0 (reset startu), Bit 1 = wynik, Bit 2 = 1 (analiza zakończona)

        self.client.db_write(DB_NUMBER, 0, bytearray([new_byte]))


def monitor_and_analyze(ip_address, rack=0, slot=1, port=102):
    linia = LiniaCnnection(ip_address, rack, slot, port)

    while True:
        try:
            if linia.read() and linia.analyze:
                print("Start analizy!")
                try:
                    # Tutaj można dodać kod do analizy danych
                    wizja_result = wizja_still()
                    print("Wynik analizy:", wizja_result)
                    if (
                        wizja_result
                        and wizja_result.get("circles")
                        and wizja_result.get("circles")[0]["color"] == "czerwony"
                    ):
                        print("Wykryto czerwone koło, zapisuję wynik jako 1...")
                        linia.result = 1
                    else:
                        print("Nie wykryto czerwonego koła, zapisuję wynik jako 0...")
                        linia.result = 0

                    linia.finished = 1
                    linia.analyze = 0
                    linia.error = 0
                except:
                    linia.error = 1

                linia.write()
                print("Analiza zakończona, wynik zapisany.")
        except Exception as e:
            print(e)

        time.sleep(0.2)


if __name__ == "__main__":
    monitor_and_analyze("127.0.0.1")  # Podaj IP swojego PLC
