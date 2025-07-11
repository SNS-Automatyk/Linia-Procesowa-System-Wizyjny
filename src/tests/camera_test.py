# This script captures a single frame from the camera and displays it in a window.


from picamera2 import Picamera2
import time
import cv2

picam2 = Picamera2()
picam2.start()
time.sleep(2)  # Allow time for the camera to adjust
frame = picam2.capture_array()
cv2.imshow("Obraz z kamery", frame)
cv2.waitKey(0)
