import os
import cv2 as cv
import datetime
import json

from .stats import Stats
from .contours import detect_contours
from .circles import detect_circles
from .annotations import annotate_frame
from .config import (
    FRAME_LEFT_MARGIN,
    FRAME_TOP_MARGIN,
    FRAME_RIGHT_MARGIN,
    FRAME_BOTTOM_MARGIN,
    STILL_REPETITION_LIMIT,
)

os.environ["LIBCAMERA_LOG_LEVELS"] = (
    "*:2"  # Ustawienie poziomu logowania dla libcamera, aby uniknąć nadmiaru informacji w konsoli
)

try:
    from picamera2 import Picamera2, Preview  # type: ignore

    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False


def get_camera():
    if PICAMERA_AVAILABLE:
        picam2 = Picamera2()
        picam2.start()
        # Zamiana kanałów BGR <-> RGB dla Picamera2
        get_frame = lambda: cv.cvtColor(picam2.capture_array(), cv.COLOR_RGB2BGR)
        release_camera = lambda: picam2.stop()
    else:
        cam = cv.VideoCapture(0)
        if not cam.isOpened():
            print("Cannot open camera")
            exit()
        get_frame = lambda: cam.read()[1]
        release_camera = lambda: cam.release()
    return get_frame, release_camera


def save_image_with_metadata(frame, result):
    save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wizja_zdjecia")
    save_dir_ann = os.path.join(save_dir, "annotated")
    save_dir_metadata = os.path.join(save_dir, "metadata")
    save_dir_raw = os.path.join(save_dir, "raw")

    os.makedirs(save_dir_raw, exist_ok=True)
    os.makedirs(save_dir_ann, exist_ok=True)
    os.makedirs(save_dir_metadata, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    filepath_plain = os.path.join(save_dir_raw, f"wizja_{timestamp}.jpg")
    filepath_ann = os.path.join(save_dir_ann, f"wizja_{timestamp}_ann.jpg")
    filepath_metadata = os.path.join(save_dir_metadata, f"wizja_{timestamp}.json")

    # Zapisz obrazek bez oznaczeń (oryginalny frame)
    cv.imwrite(filepath_plain, frame)

    # Zapisz obrazek z oznaczeniami
    annotate_frame(frame, result)
    cv.imwrite(filepath_ann, frame)

    # Zapis metadanych
    with open(filepath_metadata, "w") as f:
        json.dump(result, f)


def wizja_still(contours=False, circles=True, save_image=True):
    stats = Stats()
    stats.inc("wizja_still_calls")
    get_frame, release_camera = get_camera()
    # Odrzucenie pierwszych kilku klatek (np. 2) dla stabilizacji kamery
    for _ in range(2):
        frame = get_frame()
    if frame is None:
        print("Can't receive frame")
        release_camera()
        return

    repetition = 0
    result = None
    # Wykrywanie obiektów, aż do momentu, gdy zostaną wykryte kółka lub przekroczymy limit klatek
    while (
        repetition < STILL_REPETITION_LIMIT
        and circles
        and (not result or not result["circles"])
    ):
        frame = get_frame()
        if frame is None:
            print("Can't receive frame")
            release_camera()
            return
        repetition += 1
        result = find_objects(frame, contours=contours, circles=circles, annotate=False)

    release_camera()

    if save_image:
        save_image_with_metadata(frame, result)

    return result


def wizja_live(
    contours=False,  # Czy wykrywać kontury
    circles=True,  # Czy wykrywać kółka
):
    get_frame, release_camera = get_camera()
    while True:
        frame = get_frame()
        if frame is None:
            print("Can't receive frame")
            break
        # Wykrywanie obiektów
        find_objects(frame, contours=contours, circles=circles)
        cv.imshow("Obraz z kamery", frame)
        # cv.imshow("Krawedzie", krawedzie)
        if cv.waitKey(1) == ord("q"):
            break
    release_camera()
    cv.destroyAllWindows()


def find_objects(frame, contours=False, circles=True, annotate=True):
    results = {}
    # Wyliczanie szerokości i wysokości ramki na podstawie rozmiaru obrazu
    frame_h, frame_w = frame.shape[:2]
    FRAME_WIDTH = frame_w - FRAME_LEFT_MARGIN - FRAME_RIGHT_MARGIN
    FRAME_HEIGHT = frame_h - FRAME_TOP_MARGIN - FRAME_BOTTOM_MARGIN
    # Rysowanie ramki kadrowania na obrazie
    results["contours"] = [[], []]
    results["circles"] = []
    if contours:
        results["contours"] = detect_contours(
            frame, FRAME_LEFT_MARGIN, FRAME_TOP_MARGIN, FRAME_WIDTH, FRAME_HEIGHT
        )
    if circles:
        results["circles"] = detect_circles(
            frame, FRAME_LEFT_MARGIN, FRAME_TOP_MARGIN, FRAME_WIDTH, FRAME_HEIGHT
        )
    if annotate:
        annotate_frame(frame, results)
    return results


if __name__ == "__main__":
    wizja_live()
