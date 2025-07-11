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

def wizja_live(
        contours=False,  # Czy wykrywać kontury
        circles=True,    # Czy wykrywać kółka
):
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

    detected_circles = None
    kontury = []
    while(True):
        frame = get_frame()
        obiektow = 0
        if frame is None:
            print("Can't receive frame")
            break
        # Wyliczanie szerokości i wysokości ramki na podstawie rozmiaru obrazu
        frame_h, frame_w = frame.shape[:2]
        FRAME_WIDTH = frame_w - FRAME_LEFT_MARGIN - FRAME_RIGHT_MARGIN
        FRAME_HEIGHT = frame_h - FRAME_TOP_MARGIN - FRAME_BOTTOM_MARGIN
        # Rysowanie ramki kadrowania na obrazie
        cv.rectangle(frame, (FRAME_LEFT_MARGIN, FRAME_TOP_MARGIN), (FRAME_LEFT_MARGIN + FRAME_WIDTH, FRAME_TOP_MARGIN + FRAME_HEIGHT), (0,255,255), 2)
        # Wykrywanie konturów na całym obrazie
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        gray = cv.medianBlur(gray,5)

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

            srodki = []
            for kontur in kontury: # dla wszystkich konturów
                prostokat = cv.minAreaRect(kontur) # wyznacza najmniejszy prostokąt
                                                # zawierający dany kontur.
                                                # Zwraca współrzędne środka i
                                                # wymiary (patrz następna linia)
                ((x, y), (szer, wys), _) = prostokat # _ znaczy że zwracana wartość
                                                    # nie jest nam potrzebna
                x = int(x) # współrzędne na obrazie muszą być całkowite
                y = int(y) # tak, jak w macierzy
                # UWAGA! x oznacza nr wiersza, a y nr kolumny, więc x odpowiada za
                # pion, a y za poziom (odwrotnie niż zazwyczaj w Kartezjańskim ukłł.)


                rysuj = 1
                if szer*wys > 2000: # jeśli obiekt jest dość duży (7 dobrałem)
                    for (a, b) in srodki:

                        if abs(a-x) < 30 or abs(b-y) < 30:
                            rysuj = 0
                            break

                    if(rysuj):
                        cv.drawContours(frame, [kontur], 0, (0,0,255), 1, 1)
                        obiektow = obiektow+1
                        srodki.append((x,y))

            # Kontur i tekst liczby obiektów
            cv.putText(frame, "Detected: "+str(obiektow)+" objects", (10,30), 1, 2, (255,255,255), 2, cv.LINE_AA)
            cv.putText(frame, "Detected: "+str(obiektow)+" objects", (10,30), 1, 2, (0,0,0), 4, cv.LINE_AA)
            cv.putText(frame, "Detected: "+str(obiektow)+" objects", (10,30), 1, 2, (255,255,255), 2, cv.LINE_AA)

        if circles:
            # Wykrywanie kół na całym obrazie, ale przetwarzanie tylko tych w ramce
            detected_circles = cv.HoughCircles(gray, 
                cv.HOUGH_GRADIENT, 1, 40, param1 = 200,
                param2 = 45, minRadius = 20, maxRadius = 150
            )
            
            if detected_circles is not None:
                    
                detected_circles = np.uint16(np.around(detected_circles))

                # Usuwanie mniejszych kół wewnątrz większych
                circles = [tuple(map(int, pt)) for pt in detected_circles[0, :]]
                circles.sort(key=lambda x: -x[2])  # sortuj malejąco po promieniu
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

                # Zamiana na format do dalszego przetwarzania
                detected_circles = np.array([filtered], dtype=np.uint16)

            # Napis z liczbą kółek
            if detected_circles is not None:
                text_kolek = "Circles: "+str(len(detected_circles[0]))
            else:
                text_kolek = "Circles: 0"
            cv.putText(frame, text_kolek, (10,65), 1, 2, (0,0,0), 4, cv.LINE_AA)
            cv.putText(frame, text_kolek, (10,65), 1, 2, (255,255,255), 2, cv.LINE_AA)
                    

            if detected_circles is not None:
                for pt in detected_circles[0,:]:
                    a, b, r = int(pt[0]), int(pt[1]), int(pt[2])
                    cv.circle(frame, (a, b), r, (0, 255, 0), 2)
                    cv.circle(frame, (a, b), 1, (0, 0, 255), 3)
                    color = ""
                    average = np.array([0.0, 0.0, 0.0])
                    count = 0
                    hsv_frame = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
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
                        # Tryb (najczęstsza wartość H)
                        hue_value = int(np.bincount(np.array(hue_list, dtype=np.uint8)).argmax())
                    else:
                        hue_value = 0

                    average[0] = hue_value  # Ustawienie wartości H na średnią
                    
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

                    cv.putText(frame, color, (a,b), 1, 1, (255,255, 255))
                    # Rysowanie kwadracika w kolorze wykrytego obiektu
                    # Konwersja HSV na BGR
                    color_bgr = cv.cvtColor(np.uint8([[average]]), cv.COLOR_HSV2BGR)[0][0]
                    OFFSET_X = 0
                    OFFSET_Y = -10
                    SIZE = 20
                    rect_top_left = (a + OFFSET_X, b - OFFSET_Y)
                    rect_bottom_right = (a + OFFSET_X + SIZE, b - OFFSET_Y + SIZE)
                    cv.rectangle(frame, rect_top_left, rect_bottom_right, tuple(int(x) for x in color_bgr), -1)
                    # Ramka/kontur kwadracika (biała)
                    cv.rectangle(frame, rect_top_left, rect_bottom_right, (255,255,255), 1)


        cv.imshow("Obraz z kamery", frame)
        # cv.imshow("Krawedzie", krawedzie)
        if cv.waitKey(1) == ord('q'):
            break
    release_camera()
    cv.destroyAllWindows()

if __name__ == "__main__":
    wizja_live()