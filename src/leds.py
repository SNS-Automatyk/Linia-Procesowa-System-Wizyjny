# Sterowanie WS2812B (NeoPixel) przez GPIO (PWM) na Raspberry Pi.
# Wymaga: sudo, biblioteka rpi_ws281x

import time
import argparse
from logging import getLogger

logger = getLogger("system_wizyjny.leds")
try:
    from rpi_ws281x import PixelStrip, Color
except ImportError:
    logger.warning("Brak biblioteki rpi_ws281x. Sterowanie WS2812B będzie niedostępne.")
    PixelStrip = None
    Color = None


# Domyślna konfiguracja
LED_COUNT = 44  # liczba diod w pasku
LED_PIN = 12  # GPIO12 = PWM0
LED_FREQ_HZ = 800000  # standard WS2812B
LED_DMA = 10
LED_BRIGHTNESS = 255  # 0-255
LED_INVERT = False
LED_CHANNEL = 0  # dla GPIO18 użyj 0


class WS2812Flash:
    def __init__(self, led_count=LED_COUNT, pin=LED_PIN, brightness=LED_BRIGHTNESS):
        if PixelStrip is None:
            return
        self.strip = PixelStrip(
            led_count, pin, LED_FREQ_HZ, LED_DMA, LED_INVERT, brightness, LED_CHANNEL
        )
        self.strip.begin()

    def _fill(self, r, g, b):
        c = Color(
            r, g, b
        )  # UWAGA: wewnętrznie WS2812B często używa GRB; biblioteka mapuje to poprawnie
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, c)
        self.strip.show()

    def set_brightness(self, brightness: int):
        # 0-255; skaluje sprzętowo jasność bez zmiany kolorów
        self.strip.setBrightness(max(0, min(255, int(brightness))))
        self.strip.show()

    def flash_on(self, brightness=None):
        if brightness is not None:
            self.set_brightness(brightness)
        # biały (R,G,B) = (255,255,255)
        self._fill(130, 255, 130)

    def flash_off(self):
        self._fill(0, 0, 0)

    def flash(self, duration_ms: int = 100, brightness=None):
        self.flash_on(brightness)
        time.sleep(max(0, duration_ms) / 1000.0)
        self.flash_off()


def main():
    p = argparse.ArgumentParser(description="WS2812B flash control")
    p.add_argument("--count", type=int, default=LED_COUNT, help="liczba diod")
    p.add_argument("--pin", type=int, default=LED_PIN, help="GPIO z PWM (domyślnie 12)")
    p.add_argument("--brightness", type=int, default=LED_BRIGHTNESS, help="0-255")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("on")
    sub.add_parser("off")
    sub.add_parser("g")  # green
    sub.add_parser("r")  # red
    sub.add_parser("b")  # blue
    fp = sub.add_parser("flash")
    fp.add_argument("--ms", type=int, default=100, help="czas w milisekundach")

    args = p.parse_args()
    ctrl = WS2812Flash(args.count, args.pin, args.brightness)

    if args.cmd == "on":
        ctrl.flash_on()
    elif args.cmd == "off":
        ctrl.flash_off()
    elif args.cmd == "flash":
        ctrl.flash(args.ms)
    elif args.cmd == "g":  # green
        ctrl._fill(0, 255, 0)
    elif args.cmd == "r":  # red
        ctrl._fill(255, 0, 0)
    elif args.cmd == "b":  # blue
        ctrl._fill(0, 0, 255)


if __name__ == "__main__":
    main()
