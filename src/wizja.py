# This script captures video from a camera, detects both contours and circles in each frame, and classifies detected circles by color using HSV color space. It displays the number of detected objects and circles on the video stream.

import cv2 as cv
import numpy as np
from math import floor
from sys import getsizeof

try:
    from picamera2 import Picamera2, Preview
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False

# --- KONFIGURACJA KADROWANIA ---
FRAME_LEFT_MARGIN = 300   # Lewy margines ramki (x)
FRAME_TOP_MARGIN = 160     # Górny margines ramki (y)
FRAME_RIGHT_MARGIN = 300  # Prawy margines ramki
FRAME_BOTTOM_MARGIN = 60  # Dolny margines ramki
# --- KONIEC KONFIGURACJI ---



def get_camera():
    if PICAMERA_AVAILABLE:
        picam2 = Picamera2()
        picam2.start()
        get_frame = lambda: picam2.capture_array()
        release_camera = lambda: picam2.stop()
    else:
        cam = cv.VideoCapture(0)
        if not cam.isOpened():
            print("Cannot open camera")
            exit()
        get_frame = lambda: cam.read()[1]
        release_camera = lambda: cam.release()
    return get_frame, release_camera

def wizja_still(contours=False, circles=True):
    get_frame, release_camera = get_camera()
    # Odrzucenie pierwszych kilku klatek (np. 3) dla stabilizacji kamery
    for _ in range(4):
        frame = get_frame()
    if frame is None:
        print("Can't receive frame")
        release_camera()
        return

    repetition = 0
    result = None
    REPETITION_LIMIT = 20 # Limit powtórzeń, aby uniknąć nieskończonej pętli
    # Wykrywanie obiektów, aż do momentu, gdy zostaną wykryte kółka lub przekroczymi limit klatek
    while repetition < REPETITION_LIMIT and circles and (not result or not result['circles']):
        frame = get_frame()
        repetition += 1
        result = find_objects(frame, contours=contours, circles=circles)

    release_camera()

    # Pokaż podgląd obrazu
    # cv.imshow("Obraz z kamery", frame)
    # while(True):
    #     if cv.waitKey(1) == ord('q'):
    #         break

    return result
    
def wizja_live(
        contours=False,  # Czy wykrywać kontury
        circles=True,    # Czy wykrywać kółka
):
    get_frame, release_camera = get_camera()
    while(True):
        frame = get_frame()
        if frame is None:
            print("Can't receive frame")
            break
        # Wykrywanie obiektów
        find_objects(frame, contours=contours, circles=circles)
        cv.imshow("Obraz z kamery", frame)
        # cv.imshow("Krawedzie", krawedzie)
        if cv.waitKey(1) == ord('q'):
            break
    release_camera()
    cv.destroyAllWindows()

def get_circle_color_info(a, b, r, frame):
    hsv_frame = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
    average = np.array([0.0, 0.0, 0.0])
    count = 0
    hue_list = []
    for y in range(b - floor(r), b + floor(r)):
        for x in range(a - floor(r), a + floor(r)):
            if 0 <= y < hsv_frame.shape[0] and 0 <= x < hsv_frame.shape[1]:
                if (x - a) ** 2 + (y - b) ** 2 <= r ** 2:
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
    if average[2] < 160:
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
    return color, average

def find_objects(frame, contours=False, circles=True):
    obiektow = 0
    results = {}
    # Wyliczanie szerokości i wysokości ramki na podstawie rozmiaru obrazu
    frame_h, frame_w = frame.shape[:2]
    FRAME_WIDTH = frame_w - FRAME_LEFT_MARGIN - FRAME_RIGHT_MARGIN
    FRAME_HEIGHT = frame_h - FRAME_TOP_MARGIN - FRAME_BOTTOM_MARGIN
    # Rysowanie ramki kadrowania na obrazie
    cv.rectangle(frame, (FRAME_LEFT_MARGIN, FRAME_TOP_MARGIN), (FRAME_LEFT_MARGIN + FRAME_WIDTH, FRAME_TOP_MARGIN + FRAME_HEIGHT), (0,255,255), 2)
    # Wykrywanie konturów na całym obrazie
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    gray = cv.medianBlur(gray,5)
    results['contours'] = []
    results['circles'] = []
    if contours:
        krawedzie = cv.Canny(gray, 50, 140)
        kontury, _ = cv.findContours(krawedzie, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        # Filtracja konturów: tylko te, których środek jest w ramce
        kontury_filtered = []
        for kontur in kontury:
            M = cv.moments(kontur)
            if M['m00'] != 0:
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])
                if (FRAME_LEFT_MARGIN <= cx < FRAME_LEFT_MARGIN + FRAME_WIDTH and
                    FRAME_TOP_MARGIN <= cy < FRAME_TOP_MARGIN + FRAME_HEIGHT):
                    kontury_filtered.append(kontur)
        kontury = kontury_filtered
        results['contours'] = kontury
        srodki = []
        for kontur in kontury: # dla wszystkich konturów
            prostokat = cv.minAreaRect(kontur)
            ((x, y), (szer, wys), _) = prostokat
            x = int(x)
            y = int(y)
            rysuj = 1
            if szer*wys > 2000:
                for (a, b) in srodki:
                    if abs(a-x) < 30 or abs(b-y) < 30:
                        rysuj = 0
                        break
                if(rysuj):
                    cv.drawContours(frame, [kontur], 0, (0,0,255), 1, 1)
                    obiektow = obiektow+1
                    srodki.append((x,y))
        cv.putText(frame, "Detected: "+str(obiektow)+" objects", (10,30), 1, 2, (255,255,255), 2, cv.LINE_AA)
        cv.putText(frame, "Detected: "+str(obiektow)+" objects", (10,30), 1, 2, (0,0,0), 4, cv.LINE_AA)
        cv.putText(frame, "Detected: "+str(obiektow)+" objects", (10,30), 1, 2, (255,255,255), 2, cv.LINE_AA)
    if circles:
        detected_circles = cv.HoughCircles(gray, 
            cv.HOUGH_GRADIENT, 1, 40, param1 = 200,
            param2 = 45, minRadius = 20, maxRadius = 150
        )
        if detected_circles is not None:
            detected_circles = np.uint16(np.around(detected_circles))
            circles = [tuple(map(int, pt)) for pt in detected_circles[0, :]]
            circles.sort(key=lambda x: -x[2])
            filtered = []
            for i, (a1, b1, r1) in enumerate(circles):
                inside = False
                for (a2, b2, r2) in filtered:
                    if (a1 - a2) ** 2 + (b1 - b2) ** 2 < r2 ** 2:
                        inside = True
                        break
                if not inside and (FRAME_LEFT_MARGIN <= a1 < FRAME_LEFT_MARGIN + FRAME_WIDTH and
                        FRAME_TOP_MARGIN <= b1 < FRAME_TOP_MARGIN + FRAME_HEIGHT):
                    filtered.append((a1, b1, r1))
            detected_circles = np.array([filtered], dtype=np.uint16)
            # Zbieranie informacji o kolorze
            for pt in filtered:
                a, b, r = pt
                color, average = get_circle_color_info(a, b, r, frame)
                results['circles'].append({
                    'x': a,
                    'y': b,
                    'r': r,
                    'color': color,
                    'hsv': average.tolist()
                })
        text_kolek = "Circles: "+str(len(results['circles']))
        cv.putText(frame, text_kolek, (10,65), 1, 2, (0,0,0), 4, cv.LINE_AA)
        cv.putText(frame, text_kolek, (10,65), 1, 2, (255,255,255), 2, cv.LINE_AA)
        if detected_circles is not None:
            for pt in detected_circles[0,:]:
                a, b, r = int(pt[0]), int(pt[1]), int(pt[2])
                color, average = get_circle_color_info(a, b, r, frame)
                cv.circle(frame, (a, b), r, (0, 255, 0), 2)
                cv.circle(frame, (a, b), 1, (0, 0, 255), 3)
                cv.putText(frame, color, (a,b), 1, 1, (255,255, 255))
                color_bgr = cv.cvtColor(np.uint8([[average]]), cv.COLOR_HSV2BGR)[0][0]
                OFFSET_X = 0
                OFFSET_Y = -10
                SIZE = 20
                rect_top_left = (a + OFFSET_X, b - OFFSET_Y)
                rect_bottom_right = (a + OFFSET_X + SIZE, b - OFFSET_Y + SIZE)
                cv.rectangle(frame, rect_top_left, rect_bottom_right, tuple(int(x) for x in color_bgr), -1)
                cv.rectangle(frame, rect_top_left, rect_bottom_right, (255,255,255), 1)
    return results

if __name__ == "__main__":
    wizja_live()