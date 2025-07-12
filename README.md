# Linia Procesowa: Vision System

Software for a vision system for a process line. The project enables object detection as well as color and shape recognition (mainly circles) based on camera images. The system can be used for automatic inspection of products on a production line.

## Requirements

- Python 3.x
- OpenCV

## Installation

1. Install the required libraries:
    ```
    pip install -r requirements.txt
    ```

2. Install OpenCV:
    ```
    sudo apt-get install python3-opencv
    ```

2. Set up pre-commit hooks to ensure code quality:
    ```
    pre-commit install
    ```

## Usage
Run this to see available commands:

```python
python cli.py --help
```

Example command to run the vision system with live camera feed and circle detection:
```
python cli.py --live --circles
```

Example command to run the snap7 PLC connection and work in production mode:
```
python cli.py --plc --ip 192.168.0.1
```
where `--ip` is the IP address of the PLC.

## Configuration
The configuration file `src/config.py` contains parameters for the vision system, such as frame dimensions, margins, and limits for object detection repetitions. You can adjust these parameters to fit your specific use case.

## Authors

Project created as part of work on a vision system for a process line