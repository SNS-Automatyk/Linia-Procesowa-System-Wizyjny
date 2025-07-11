# This script captures video from a camera, detects contours and objects in each frame, and classifies their color using HSV color space. It displays the number and color of detected objects on the video stream.


import cv2 as cv
import cv2
import numpy as np
from sys import getsizeof



cam = cv.VideoCapture("/dev/video2")

if not cam.isOpened():     # Jeśli kamera się nie otworzyła poprawnie
    cam.open("/dev/video2")# to następuje próba jej otwarcia.
    if not cam.isOpened():
        print("Nie udało się połączyć z kamerą") # Jak się nie uda,
        exit()                                   # program się kończy.
#---------------------------------------------------------------------------

kontury = None    
#licznik = 0
# PĘTLA Z POBIERANIEM KLATEK ===============================================
while(True):
    czy_sie_powiodlo, klatka = cam.read() # wczytanie klatki
    #licznik = licznik+1
    obiektow=0
    if not czy_sie_powiodlo:
        print("Nie można wczytać klatki")
        break
  
    	
    hsv = cv.cvtColor(klatka, cv.COLOR_BGR2HSV)
    szary = cv.cvtColor(klatka, cv.COLOR_BGR2GRAY)
    szary = cv.medianBlur(szary, 5)

    
    krawedzie = cv.Canny(szary, 50, 140) # Algorytm Canny'ego wykrywający
                                         # krawędzie (dwa ostatnie argumenty
                                         # to progi do progowania z histerezą)

    # funkcja wyodrębniająca kontury z obrazu (czarno-białego obrazu z
    # krawędziami, który zwróciła funkcja Canny()) Drugi argumet określa,
    # że interesują nas tylko zewnętrzne kontury, a 3. mówi, że proste odcinki
    # konturów będą przybliżane przez mniejszą liczbę punktów
    his_kontury = kontury
    kontury, _ = cv.findContours(krawedzie, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    
    if getsizeof(kontury) < getsizeof(his_kontury):
    	kontury = his_kontury

    srodki = []
    for kontur in kontury: # dla wszystkich konturów
        prostokat = cv.minAreaRect(kontur) # wyznacza najmniejszy prostokąt
                                           # zawierający dany kontur.
                                           # Zwraca współrzędne środka i
                                           # wymiary (patrz następna linia)
        ((x, y), (szer, wys), _) = prostokat # _ znaczy że zwracana wartość
                                             # nie jest nam potrzebna
        x = int(x) 
        y = int(y) 
        
        wierzcholki = cv.boxPoints(prostokat) #konwersja formatów
        wierzcholki = np.int0(wierzcholki)
        rysuj = 1
        if szer*wys > 2000: # jeśli obiekt jest dość duży (7 dobrałem)
            for (a, b) in srodki:

                if abs(a-x) < 30 or abs(b-y) < 30:
                    rysuj = 0
                    break

            if(rysuj):
                h = hsv[y][x][0]
                if h < 25:
                    kolor = "czerwony"
                elif h < 70:
                    kolor = "zielony"
                elif h < 140:
                    kolor = "niebieski"
                else:
                    kolor = "czerwony"

                if hsv[y][x][1] < 30:
                    kolor = "bialy"
                if hsv[y][x][2] < 30:
                    kolor = "czarny"
                    
                cv.putText(klatka, kolor, (x,y), 1, 1, (255,255, 255))

                cv.drawContours(klatka, [wierzcholki], 0, (0,0,255), 1, 1)
                obiektow = obiektow+1
                srodki.append((x,y))


        cv.putText(klatka, "Wykryto: "+str(obiektow)+" obiekty", (270,330), 1, 1, (255,255, 255))
    cv.imshow("Obraz z kamery", klatka)
    
                                        
    if cv.waitKey(1) == ord('q'):
        break

cam.release()        
cv.destroyAllWindows() 
