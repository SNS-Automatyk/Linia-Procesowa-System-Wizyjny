import argparse
from src.wizja import wizja_live

def main():
    parser = argparse.ArgumentParser(description='CLI for linia project')
    parser.add_argument('-l', '--live', action='store_true', help='Run live vision')
    parser.add_argument('-c', '--circles', action='store_true', help='Enable circle detection')
    parser.add_argument('-k', '--contours', action='store_true', help='Enable contour detection')
    args = parser.parse_args()

    if args.live:
        print('Uruchamianie wizji live...')
        wizja_live(
            contours=args.contours,
            circles=args.circles
        )
    else:
        print('No option selected. Use --help for more information.')

if __name__ == '__main__':
    main()
