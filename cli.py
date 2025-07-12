import argparse
from src.wizja import wizja_live, wizja_still


def main():
    parser = argparse.ArgumentParser(description="CLI for linia project")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-l", "--live", action="store_true", help="Run live vision")
    group.add_argument("-s", "--static", action="store_true", help="Run static vision")
    group.add_argument("-p", "--plc", action="store_true", help="Run PLC connection")

    parser.add_argument(
        "-c", "--circles", action="store_true", help="Enable circle detection"
    )
    parser.add_argument(
        "-k", "--contours", action="store_true", help="Enable contour detection"
    )
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="PLC IP address")
    args = parser.parse_args()

    if args.live:
        print("Uruchamianie wizji live...")
        wizja_live(contours=args.contours, circles=args.circles)
    elif args.static:
        print("Uruchamianie wizji statycznej...")
        reponse = wizja_still(contours=args.contours, circles=args.circles)
        print("Wynik analizy:", reponse)
        # input('Naciśnij Enter, aby zakończyć...')
    elif args.plc:
        print("Uruchamianie połączenia z PLC...")
        from src.plc_connection import monitor_and_analyze

        monitor_and_analyze(args.ip)
    else:
        print("No option selected. Use --help for more information.")


if __name__ == "__main__":
    main()
