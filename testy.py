# This script captures a single frame from the camera and displays it in a window.

import cv2 as cv
import numpy as np
from math import floor
cam = cv.VideoCapture("/dev/video0")


if not cam.isOpened():
    print("Cannot open camera")
    exit()


ret, frame = cam.read()
 
cv.imshow("Obraz z kamery", frame)


