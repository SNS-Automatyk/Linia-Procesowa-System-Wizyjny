"""
Skrypt ewaluacyjny: przetwarza obrazy z folderu i sprawdza, czy dla każdego obrazu
funkcja detect_circles wykrywa dokładnie 1 koło.

Użycie:
  - Przez zmienną środowiskową IMAGES_PATH:
	  IMAGES_PATH=/ścieżka/do/obrazów python -m src.tests.saved_images_test

  - Lub parametrem CLI:
	  python -m src.tests.saved_images_test --images /ścieżka/do/obrazów

Opcje:
  --images, -i   Ścieżka do folderu z obrazami (rekurencyjnie)
  --ext, -e      Rozszerzenia obrazów (lista po przecinku). Domyślnie: jpg,jpeg,png,bmp
  --verbose, -v  Wypisz wynik dla każdego pliku
	--search       Uruchom przeszukiwanie siatką (grid search) dla param1/param2
	--p1, --param1 Zakres i krok dla param1 w formacie min:max:step (domyślnie 80:240:20)
	--p2, --param2 Zakres i krok dla param2 w formacie min:max:step (domyślnie 20:80:5)
	--topk         Ile najlepszych kombinacji wypisać (domyślnie 5)

Kryterium poprawności: dokładnie 1 wykryte koło.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Tuple

import cv2 as cv
import numpy as np  # for ndarray type hints

try:  # optional progress bar via rich
    from rich.progress import (
        Progress,
        BarColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )

    _HAS_RICH = True
except Exception:  # pragma: no cover
    _HAS_RICH = False


# Zapewnij możliwość importu modułu jako "src.circles"
# (dodajemy katalog nadrzędny nad folderem "src" do sys.path)
_THIS_DIR = os.path.abspath(os.path.dirname(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.circles import detect_circles  # noqa: E402
from src.annotations import annotate_frame


def find_image_files(images_dir: str, extensions: Tuple[str, ...]) -> List[str]:
    files: List[str] = []
    for root, _dirs, filenames in os.walk(images_dir):
        for name in filenames:
            if name.lower().endswith(extensions):
                files.append(os.path.join(root, name))
    files.sort()
    return files


def process_image(path: str, verbose: bool = False) -> Tuple[bool | None, int | str]:
    """Zwraca (ok, count_or_reason).

    ok = True  -> dokładnie 1 koło
    ok = False -> 0 lub >1 kół
    ok = None  -> plik nieczytelny
    """
    img = cv.imread(path)
    if img is None:
        if verbose:
            print(f"UNREADABLE: {path}")
        return None, "nie można wczytać obrazu"

    h, w = img.shape[:2]
    circles = detect_circles(img, 0, 0, w, h)
    count = len(circles)
    ok = count == 1
    if verbose:
        status = "OK" if ok else "ERR"
        print(f"{status} {os.path.basename(path)}: {count} kół")
    return ok, count, circles


def _parse_range(spec: str, default: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Parsuje zapis min:max:step do krotki liczb całkowitych.

    Zwraca (min, max, step). Gdy spec jest None lub niepoprawny, zwraca default.
    """
    try:
        if not spec:
            return default
        parts = [int(x.strip()) for x in spec.split(":")]
        if len(parts) != 3:
            return default
        pmin, pmax, pstep = parts
        if pstep <= 0 or pmax < pmin:
            return default
        return pmin, pmax, pstep
    except Exception:
        return default


def _grid_values(vmin: int, vmax: int, vstep: int) -> List[int]:
    vals: List[int] = []
    cur = vmin
    while cur <= vmax:
        vals.append(int(cur))
        cur += vstep
    return vals


def _load_images(files: List[str]) -> Tuple[List[Tuple[str, "np.ndarray"]], List[str]]:
    """Ładuje obrazy do pamięci raz, zwraca listę (path, img) i listę nieczytelnych."""
    loaded: List[Tuple[str, "np.ndarray"]] = []
    unreadable: List[str] = []
    for fp in files:
        img = cv.imread(fp)
        if img is None:
            unreadable.append(fp)
        else:
            loaded.append((fp, img))
    return loaded, unreadable


def evaluate_combo(
    loaded_imgs: List[Tuple[str, "np.ndarray"]],
    param1: int,
    param2: int,
) -> Tuple[int, int, int, int]:
    """Ocena danej pary (param1, param2).

    Zwraca (ok_count, zero_count, many_count, total_readable).
    """
    ok_count = 0
    zero_count = 0
    many_count = 0
    for _fp, img in loaded_imgs:
        h, w = img.shape[:2]
        circles = detect_circles(
            img, 0, 0, w, h, params={"param1": param1, "param2": param2}
        )
        cnt = len(circles)
        if cnt == 1:
            ok_count += 1
        elif cnt == 0:
            zero_count += 1
        else:
            many_count += 1
    return ok_count, zero_count, many_count, len(loaded_imgs)


def run_grid_search(
    files: List[str],
    p1_range: Tuple[int, int, int],
    p2_range: Tuple[int, int, int],
    topk: int = 5,
) -> None:
    """Przeszukuje param1/param2 po siatce i wypisuje najlepsze kombinacje."""
    loaded, unreadable = _load_images(files)
    if not loaded:
        print("Brak czytelnych obrazów do ewaluacji.")
        return

    p1_vals = _grid_values(*p1_range)
    p2_vals = _grid_values(*p2_range)
    total_combos = len(p1_vals) * len(p2_vals)
    print(
        f"Start grid search: param1 in {p1_vals} (n={len(p1_vals)}), param2 in {p2_vals} (n={len(p2_vals)}); łącznie {total_combos} kombinacji, obrazy={len(loaded)}, nieczytelne={len(unreadable)}"
    )

    results: List[Tuple[int, int, int, int, int, int]] = []

    # tuple: (ok, zero, many, total, p1, p2)
    def _loop_and_collect(progress_obj=None, task_id=None):
        idx = 0
        plain_stride = max(1, total_combos // 50)
        for p1 in p1_vals:
            for p2 in p2_vals:
                okc, zeroc, manyc, total = evaluate_combo(loaded, p1, p2)
                results.append((okc, zeroc, manyc, total, p1, p2))
                idx += 1
                if progress_obj is not None and task_id is not None:
                    progress_obj.advance(task_id)
                elif not _HAS_RICH and idx % plain_stride == 0:
                    pct = int(100 * idx / total_combos)
                    print(f"… {idx}/{total_combos} ({pct}%)", end="\r", flush=True)

    try:
        if _HAS_RICH:
            with Progress(
                "{task.description}",
                BarColumn(bar_width=None),
                "{task.completed}/{task.total}",
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            ) as progress:
                task = progress.add_task("Grid search", total=total_combos)
                _loop_and_collect(progress, task)
        else:
            _loop_and_collect()
            if total_combos:
                print("\nZakończono przeszukiwanie.")
    except KeyboardInterrupt:
        print("\nPrzerwano przez użytkownika. Prezentuję dotychczasowe wyniki…")

    # sortowanie: najpierw max OK, potem min many(>1), potem min zero, potem mniejszy param1/param2
    results.sort(key=lambda x: (-x[0], x[2], x[1], x[4], x[5]))

    best = results[0]
    best_ok, best_zero, best_many, best_total, best_p1, best_p2 = best
    print("\n== Najlepsza kombinacja ==")
    print(
        f"param1={best_p1}, param2={best_p2} -> OK={best_ok}/{best_total} (zero={best_zero}, >1={best_many})"
    )

    print("\nTop kombinacje:")
    for i, (okc, zeroc, manyc, total, p1, p2) in enumerate(
        results[: max(1, topk)], start=1
    ):
        ratio = 100.0 * okc / total if total else 0.0
        print(
            f"{i:2d}. p1={p1:3d}, p2={p2:3d} -> OK={okc}/{total} ({ratio:.1f}%), zero={zeroc}, >1={manyc}"
        )

    print(
        '\nWskazówka: możesz użyć tych parametrów w detect_circles: params={"param1": '
        + str(best_p1)
        + ', "param2": '
        + str(best_p2)
        + "}"
    )


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ewaluacja wykrywania kół na zbiorze obrazów"
    )
    parser.add_argument(
        "-i",
        "--images",
        default=os.environ.get("IMAGES_PATH"),
        help="Ścieżka do folderu z obrazami (domyślnie z IMAGES_PATH)",
    )
    parser.add_argument(
        "-e",
        "--ext",
        default="jpg,jpeg,png,bmp",
        help="Lista rozszerzeń obrazów po przecinku (domyślnie: jpg,jpeg,png,bmp)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Szczegółowe logi per-plik"
    )
    parser.add_argument(
        "--search",
        action="store_true",
        help="Uruchom przeszukiwanie (grid search) param1/param2",
    )
    parser.add_argument(
        "--p1",
        "--param1",
        dest="p1",
        default="80:240:20",
        help="Zakres dla param1: min:max:step (domyślnie 80:240:20)",
    )
    parser.add_argument(
        "--p2",
        "--param2",
        dest="p2",
        default="20:80:5",
        help="Zakres dla param2: min:max:step (domyślnie 20:80:5)",
    )
    parser.add_argument(
        "--topk",
        type=int,
        default=5,
        help="Ile najlepszych kombinacji wypisać (domyślnie 5)",
    )
    parser.add_argument(
        "-s",
        "--save",
        action="store_true",
        help="Zapisz obrazy z adnotacjami do folderu output_images",
    )

    args = parser.parse_args(argv)

    if not args.images:
        parser.error("Podaj --images lub ustaw zmienną środowiskową IMAGES_PATH")

    images_dir = os.path.abspath(args.images)
    if not os.path.isdir(images_dir):
        parser.error(f"Katalog nie istnieje: {images_dir}")

    exts = tuple(
        "." + e.strip().lstrip(".").lower() for e in args.ext.split(",") if e.strip()
    )
    files = find_image_files(images_dir, exts)

    if not files:
        print(f"Brak plików obrazów w {images_dir} dla rozszerzeń: {', '.join(exts)}")
        return 2

    # Tryb przeszukiwania siatką parametrów
    if args.search:
        p1_range = _parse_range(args.p1, (80, 240, 20))
        p2_range = _parse_range(args.p2, (20, 80, 5))
        run_grid_search(files, p1_range, p2_range, topk=args.topk)
        return 0

    total = len(files)
    ok_count = 0
    bad: List[Tuple[str, int]] = []
    unreadable: List[str] = []

    for fp in files:
        ok, count, circles = process_image(fp, args.verbose)
        if ok is None:
            unreadable.append(fp)
        elif ok:
            ok_count += 1
        else:
            bad.append((fp, int(count)))
        if args.save and count > 0:
            img = cv.imread(fp)
            annotate_frame(img, {"circles": circles})

            # gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
            # gray = cv.medianBlur(gray, 5)
            # param1 = 100  # Adjusted param1 for Canny
            # edges = cv.Canny(gray, param1 // 2, param1)
            # # put edges on img for visualization and save
            # img = cv.cvtColor(edges, cv.COLOR_GRAY2BGR)
            # img[:, :, 2] = edges  # put edges on red channel
            # cv.imshow("edges", edges)
            # cv.waitKey(0)
            # cv.destroyAllWindows()

            output_dir = os.path.join(
                "output_images", os.path.relpath(os.path.dirname(fp), images_dir)
            )
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, os.path.basename(fp))
            cv.imwrite(output_path, img)

    bad_count = len(bad)
    unreadable_count = len(unreadable)

    print("\n== Podsumowanie ==")
    print(f"Wszystkie pliki:      {total}")
    print(f"Poprawne (1 koło):    {ok_count}")
    print(f"Niepoprawne (!=1):    {bad_count}")
    if unreadable_count:
        print(f"Nieczytelne:          {unreadable_count}")

    if bad_count:
        print("\nPrzykłady niepoprawnych (pierwsze 10):")
        for fp, c in bad[:10]:
            print(f"- {os.path.relpath(fp, images_dir)} -> {c} kół")

    # Kod wyjścia: 0 jeśli wszystko OK; 1 jeśli są niepoprawne; 2 jeśli brak plików
    return 0 if bad_count == 0 and unreadable_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
