# This script captures video from a camera, detects significant frame changes, and uses Hough Circle Transform to detect circles. For each detected circle, it estimates the color based on the average HSV values inside the circle and displays the result on the video stream
import cv2 as cv
import numpy as np
from math import floor
cam = cv.VideoCapture("/dev/video0")


if not cam.isOpened():
    print("Cannot open camera")
    exit()


ret, frame = cam.read()
gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
while(True):
    oldgray = gray
    ret, frame = cam.read()
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    gray_blurred = cv.blur(gray, (3, 3))
    
    diffrence = cv.absdiff(gray, oldgray)
    suma = 0
    for pixel in diffrence:
        suma += pixel[0]
   
    print(suma)
    if suma > 1500:
        if not ret:
            print("Can't receive frame")
            break
        print(frame.shape)
        
        
        detected_circles = cv.HoughCircles(gray_blurred, 
                       cv.HOUGH_GRADIENT, 1, 70, param1 = 50,
                   param2 = 35, minRadius = 30, maxRadius = 180)
        if detected_circles is not None:
            detected_circles = np.uint16(np.around(detected_circles))
            
    for pt in detected_circles[0,:]:
                a, b, r = pt[0], pt[1], pt[2]
            
                cv.circle(frame, (a, b), r, (0, 255, 0), 2)
                cv.circle(frame, (a, b), 1, (0, 0, 255), 3)
                color = ""
                colors = ["niebieski", "zielony", "czerwony"]
                average = [0, 0, 0]

                hsv_frame = cv.cvtColor(frame, cv.COLOR_BGR2HSV)

                for i in range(a-floor(r/2)-1, a+floor(r/2)-1):
                    for j in range(b-floor(r/2), b+floor(r/2)-1):
                        if(i<480 and j<640):
                            average += hsv_frame[i,j,:]
                average[0] /= r*r+1
                average[1] /= r*r+1
                average[2] /= r*r+1
                hue_value = average[0]

                if average[2] < 90:
                    color = "czarny"
                elif average[0] < 5:
                    color = "czerwony"
                elif hue_value < 22:
                    color = "pomarńczowy"
                elif hue_value < 33:
                    color = "żółty"
                elif hue_value < 78:
                    color = "zielony"
                elif hue_value < 131:
                    color = "niebieski"
                elif hue_value < 170:
                    color = "fioletowy"

                cv.putText(frame, color, (a,b), 5, 5, (255,255, 255))
     
    
    cv.imshow("Obraz z kamery", frame)
    if cv.waitKey(1) == ord('q'):
        break
cam.release()
cv.destroyAllWindows()
