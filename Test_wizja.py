import cv2 as cv
import numpy as np
from math import floor
from sys import getsizeof

cam = cv.VideoCapture(-1)


if not cam.isOpened():
    print("Cannot open camera")
    exit()



ret, frame = cam.read()

#cv.imshow("Obraz z kamery", frame)
detected_circles = None
old_detected_circles = None
number_detected_circles = 0
licznik = 0
kontury = []
while(True):
    ret, frame = cam.read()
    print(frame)
    licznik = licznik+1
    obiektow = 0
    if not ret:
        print("Can't receive frame")
        cv.imshow("Obraz z kamery", frame)
        continue
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    gray = cv.medianBlur(gray,5)

     # konwesja na szary obraz
                                   # Funkcja w każdy kwadrat 3x3 (2. argument)
                                   # zastępuje medianą, przez co niweluje szum
                                   # Wersja z medianą (zamiast średniej)
                                   # lepiej zachowuje krawędzie
    
    #high_thresh, thresh_im = cv.threshold(szary, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
    #lowThresh = 0.5*high_thresh
 
    krawedzie = cv.Canny(gray, 50, 140) # Algorytm Canny'ego wykrywający
                                         # krawędzie (dwa ostatnie argumenty
                                         # to progi do progowania z histerezą)

    # funkcja wyodrębniająca kontury z obrazu (czarno-białego obrazu z
    # krawędziami, który zwróciła funkcja Canny()) Drugi argumet określa,
    # że interesują nas tylko zewnętrzne kontury, a 3. mówi, że proste odcinki
    # konturów będą przybliżane przez mniejszą liczbę punktów
    his_kontury = kontury
    kontury, _ = cv.findContours(krawedzie, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    print('b')
    if getsizeof(kontury) < getsizeof(his_kontury) and licznik < 50:
        kontury = his_kontury
    
    if licznik > 150:
        licznik= 0

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
        # pion, a y za poziom (odwrotnie niż zazwyczaj w Kartezjańskim ukł.)
        
        wierzcholki = cv.boxPoints(prostokat) #konwersja formatów
        wierzcholki = np.int0(wierzcholki)
        rysuj = 1
        print('c')
        if szer*wys > 2000: # jeśli obiekt jest dość duży (7 dobrałem)
            for (a, b) in srodki:

                if abs(a-x) < 30 or abs(b-y) < 30:
                    rysuj = 0
                    break

            if(rysuj):
                cv.drawContours(frame, [wierzcholki], 0, (0,0,255), 1, 1)
                obiektow = obiektow+1
                srodki.append((x,y))

    cv.putText(frame, "Wykryto: "+str(obiektow)+" obiekty", (270,330), 1, 1, (255,255, 255))


    old_detected_circles = detected_circles
    detected_circles = cv.HoughCircles(gray, 
                       cv.HOUGH_GRADIENT, 1, 40, param1 = 200,
                       param2 = 45, minRadius = 20, maxRadius = 150)
    if detected_circles is not None and old_detected_circles is not None:
        if detected_circles.size < old_detected_circles.size:
            detected_circles = old_detected_circles
            
        detected_circles = np.uint16(np.around(detected_circles))

        cv.putText(frame, "Kolek: "+str(int(detected_circles.size/3)), (270,360), 1, 1, (255,255, 255))
        cv.imshow("Obraz z kamery", frame)
        cv.imshow("Krawedzie", krawedzie)
        print('e')
        if cv.waitKey(1) == ord('q'):
            break
cam.release()
cv.destroyAllWindows()