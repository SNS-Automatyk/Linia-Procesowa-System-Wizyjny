import cv2 as cv
import numpy as np
from math import floor

from .stats import Stats
from .config import CIRCLE_MIN_RADIUS, CIRCLE_MAX_RADIUS


def detect_circles(
    frame, FRAME_LEFT_MARGIN, FRAME_TOP_MARGIN, FRAME_WIDTH, FRAME_HEIGHT, params={}
):
    results_circles = []
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    gray = cv.medianBlur(gray, 5)
    param1 = params.get("param1", 15)
    param2 = params.get("param2", 35)
    detected_circles = cv.HoughCircles(
        gray,
        cv.HOUGH_GRADIENT,
        dp=1,  # odwrotność skali akumulatora względem obrazu. 1 = ta sama rozdzielczość; >1 zmniejsza rozdzielczość akumulatora (szybciej, ale mniej dokładnie).
        minDist=(
            CIRCLE_MIN_RADIUS * 2
        ),  # minimalna odległość między środkami wykrytych okręgów (w pikselach). Za małe → duplikaty; za duże → pomijanie bliskich okręgów.
        param1=param1,
        # param1 – górny próg dla Canny:
        # HoughCircles wewnętrznie uruchamia Canny(low=param1/2, high=param1).
        # Wyższy param1 → mniej krawędzi (bardziej „pewne” krawędzie), mniejszy szum, ale ryzyko utraty słabych okręgów.
        # Niższy param1 → więcej krawędzi (także szumu), koła łatwiej „zbierają” głosy, ale rośnie liczba fałszywych detekcji.
        # Typowe zakresy: 100–250.
        param2=param2,
        # param2 – próg akumulatora dla środków okręgów:
        # Minimalna liczba „głosów” z krawędzi, aby uznać punkt za środek koła.
        # Wyższy param2 → mniej detekcji, ale bardziej pewne; zbyt wysoki gubi słabsze/małe koła.
        # Niższy param2 → więcej detekcji, także fałszywych/duplikatów (zwłaszcza przy niskim param1).
        # Czułość param2 zależy od dp i zakresu promieni: dla mniejszych kół zwykle trzeba go obniżyć.
        # Typowe zakresy: 20–80.
        #  Jak je stroić w praktyce:
        # Najpierw ustaw minRadius/maxRadius możliwie wąsko dla Twoich obiektów.
        # Dobierz param1 patrząc na krawędzie Canny – krawędź koła powinna być ciągła, tło możliwie czyste.
        # Podgląd krawędzi:
        #         gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        # gray = cv.medianBlur(gray, 5)
        # edges = cv.Canny(gray, param1 // 2, param1)
        # cv.imshow("edges", edges)
        # Potem reguluj param2:
        # Brak/mało kół → obniż param2 (np. 45 → 35) lub nieco obniż param1 (200 → 150).
        # Za dużo fałszywych/duplikatów → podnieś param2 (np. 45 → 60) lub podnieś param1 (200 → 230).
        # Pamiętaj: gdy zwiększysz dp (>1), akumulator ma mniejszą rozdzielczość i często trzeba nieco obniżyć param2.
        # Dla Twoich bieżących wartości (param1=200, param2=45):
        minRadius=CIRCLE_MIN_RADIUS,
        maxRadius=CIRCLE_MAX_RADIUS,
    )
    filtered = []
    if detected_circles is not None:
        detected_circles = np.uint16(np.around(detected_circles))
        circles = [tuple(map(int, pt)) for pt in detected_circles[0, :]]
        circles.sort(key=lambda x: -x[2])
        for i, (a1, b1, r1) in enumerate(circles):
            inside = False
            for a2, b2, r2 in filtered:
                if (a1 - a2) ** 2 + (b1 - b2) ** 2 < r2**2:
                    inside = True
                    break
            if not inside and (
                FRAME_LEFT_MARGIN <= a1 < FRAME_LEFT_MARGIN + FRAME_WIDTH
                and FRAME_TOP_MARGIN <= b1 < FRAME_TOP_MARGIN + FRAME_HEIGHT
            ):
                filtered.append((a1, b1, r1))
        detected_circles = np.array([filtered], dtype=np.uint16)

    if detected_circles is not None:
        for pt in detected_circles[0, :]:
            a, b, r = int(pt[0]), int(pt[1]), int(pt[2])
            color, average = get_circle_color_info(a, b, r, frame)
            results_circles.append(
                {"x": a, "y": b, "r": r, "color": color, "hsv": average.tolist()}
            )

    return results_circles


def get_circle_color_info(a, b, r, frame):
    hsv_frame = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
    average = np.array([0.0, 0.0, 0.0])
    count = 0
    hue_list = []
    for y in range(b - floor(r), b + floor(r)):
        for x in range(a - floor(r), a + floor(r)):
            if 0 <= y < hsv_frame.shape[0] and 0 <= x < hsv_frame.shape[1]:
                if (x - a) ** 2 + (y - b) ** 2 <= r**2:
                    average += hsv_frame[y, x, :]
                    count += 1
                    hue_list.append(hsv_frame[y, x, 0])
    if count > 0:
        average /= count
    if hue_list:
        hue_value = int(np.bincount(np.array(hue_list, dtype=np.uint8)).argmax())
    else:
        hue_value = 0
    average[0] = hue_value
    if average[2] < 80 or (average[2] < 150 and average[1] < 100):
        color = "czarny"
    elif hue_value < 7.5:
        color = "czerwony"
    elif hue_value < 19:
        color = "pomaranczowy"
    elif hue_value < 35:
        color = "zolty"
    elif hue_value < 80:
        color = "zielony"
    elif hue_value < 122.5:
        color = "niebieski"
    elif hue_value < 140:
        color = "fioletowy"
    elif hue_value < 162.5:
        color = "rozowy"
    else:
        color = "czerwony"

    stats = Stats()
    stats.inc(f"wizja_color_{color}")
    return color, average
