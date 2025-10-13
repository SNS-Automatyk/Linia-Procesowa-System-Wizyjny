import asyncio
import os
import cv2 as cv
import datetime
import json
import logging


logger = logging.getLogger("system_wizyjny")
logger.setLevel(logging.DEBUG)


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
from .camera import Camera


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


def wizja_still(
    contours=False,
    circles=True,
    save_image=True,
    camera=None,
    stop_event=None,
):
    
    if camera is None:
        camera = Camera()
    stats = Stats()
    stats.inc("wizja_still_calls")

    cancelled = False
    frame = None
    result = None
    try:
        repetition = 0
        # Wykrywanie obiektów, aż do momentu, gdy zostaną wykryte kółka lub przekroczymy limit klatek
        while (
            repetition < STILL_REPETITION_LIMIT
            and circles
            and (not result or not result.get("circles"))
        ):
            if stop_event and stop_event.is_set():
                cancelled = True
                break
            frame = camera.get_frame()
            if frame is None:
                print("Can't receive frame")
                logger.error("Can't receive frame")
                return None
            repetition += 1
            result = find_objects(
                frame, contours=contours, circles=circles, annotate=False
            )
    finally:
        camera.release()

    if cancelled:
        return result

    if save_image and frame is not None:
        save_image_with_metadata(frame, result)

    return result


def wizja_live(
    contours=False,  # Czy wykrywać kontury
    circles=True,  # Czy wykrywać kółka
    camera=None,  # Obiekt kamery (jeśli None, zostanie utworzony nowy)
):
    if not camera:
        camera = Camera()
    while True:
        frame = camera.get_frame()
        if frame is None:
            print("Can't receive frame")
            break
        # Wykrywanie obiektów
        find_objects(frame, contours=contours, circles=circles)
        cv.imshow("Obraz z kamery", frame)
        # cv.imshow("Krawedzie", krawedzie)
        if cv.waitKey(1) == ord("q"):
            break
    camera.release()
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
