import cv2 as cv
import numpy as np

from .config import (
    FRAME_LEFT_MARGIN,
    FRAME_TOP_MARGIN,
    FRAME_RIGHT_MARGIN,
    FRAME_BOTTOM_MARGIN,
)


def put_text_with_shadow(
    frame,
    text,
    position,
    font_scale=1,
    thickness=2,
    color=(255, 255, 255),
    shadow_color=(0, 0, 0),
):

    cv.putText(
        frame,
        text,
        position,
        font_scale,
        thickness,
        shadow_color,
        4,
        cv.LINE_AA,
    )
    cv.putText(
        frame,
        text,
        position,
        font_scale,
        thickness,
        color,
        2,
        cv.LINE_AA,
    )


def annotate_frame(frame, data):

    # Frame size annotations
    frame_h, frame_w = frame.shape[:2]
    FRAME_WIDTH = frame_w - FRAME_LEFT_MARGIN - FRAME_RIGHT_MARGIN
    FRAME_HEIGHT = frame_h - FRAME_TOP_MARGIN - FRAME_BOTTOM_MARGIN
    cv.rectangle(
        frame,
        (FRAME_LEFT_MARGIN, FRAME_TOP_MARGIN),
        (FRAME_LEFT_MARGIN + FRAME_WIDTH, FRAME_TOP_MARGIN + FRAME_HEIGHT),
        (0, 255, 255),
        2,
    )

    # Circles annotations
    for circle in data.get("circles", []):
        a = circle["x"]
        b = circle["y"]
        r = circle["r"]
        color = circle["color"]
        average = circle["hsv"]
        OFFSET_X = 0
        OFFSET_Y = -10
        SIZE = 20
        color_bgr = cv.cvtColor(np.uint8([[average]]), cv.COLOR_HSV2BGR)[0][0]
        rect_top_left = (a + OFFSET_X, b - OFFSET_Y)
        rect_bottom_right = (a + OFFSET_X + SIZE, b - OFFSET_Y + SIZE)
        cv.circle(frame, (a, b), r, (0, 255, 0), 2)
        cv.circle(frame, (a, b), 1, (0, 0, 255), 3)
        cv.putText(
            frame,
            f"{color} HSV:{[int(round(x)) for x in average]}",
            (a, b),
            1,
            1,
            (255, 255, 255),
        )
        cv.rectangle(
            frame,
            rect_top_left,
            rect_bottom_right,
            tuple(int(x) for x in color_bgr),
            -1,
        )
        cv.rectangle(frame, rect_top_left, rect_bottom_right, (255, 255, 255), 1)

    # Circle count annotation
    put_text_with_shadow(
        frame,
        f"Circles: {len(data.get('circles', []))}",
        (10, 65),
    )

    # Contours annotations
    for kontur in data.get("contours", [[]])[0]:
        cv.drawContours(frame, [kontur], 0, (0, 0, 255), 1, 1)

    obiekty = data.get("contours", [[], []])[1]
    # Contour count annotation
    put_text_with_shadow(
        frame,
        f"Detected: {len(obiekty)} objects",
        (10, 30),
    )

    for obiekt in obiekty:
        x, y = obiekt
        cv.circle(frame, (x, y), 5, (0, 255, 0), -1)
        cv.putText(frame, f"({x}, {y})", (x + 10, y), 1, 1, (255, 255, 255))
