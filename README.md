# Linia Procesowa: Vision System

Software for a vision system for a process line. The project enables object detection as well as color and shape recognition (mainly circles) based on camera images. The system can be used for automatic inspection of products on a production line.

## Requirements

- Python 3.x
- OpenCV (`opencv-python`)
- NumPy

## Script Descriptions

### Camera.py
Captures video from a camera, detects significant frame changes, and uses Hough Circle Transform to detect circles. For each detected circle, it estimates the color based on the average HSV values inside the circle and displays the result on the video stream.

### Camera_dziala.py
Captures video from a camera, detects significant changes between consecutive frames, and applies Hough Circle Transform to detect circles. It estimates the color of each detected circle using HSV color space and displays the results on the video stream.

### rozpoznawanie_obiektow3.py
Captures video from a camera, detects contours and objects in each frame, and classifies their color using HSV color space. It displays the number and color of detected objects on the video stream.

### system_wizyjny (1).py
Captures video from a camera, detects both contours and circles in each frame, and classifies detected circles by color using HSV color space. It displays the number of detected objects and circles on the video stream.

### Test_wizja.py
Captures video from a camera, detects contours and circles in each frame, and displays debug information about the detection process. It shows the number of detected objects and circles on the video stream.

### testy.py
Captures a single frame from the camera and displays it in a window.

### Wizja.py
Captures video from a camera, detects both contours and circles in each frame, and classifies detected circles by color using HSV color space. It displays the number of detected objects and circles on the video stream.

## Installation

1. Install the required libraries:
    ```
    pip install opencv-python numpy
    ```

2. Run the selected script:
    ```
    python Camera.py
    ```

## Authors

Project created as part of work on a vision system for a process line