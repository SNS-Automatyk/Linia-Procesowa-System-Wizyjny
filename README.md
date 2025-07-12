# Linia Procesowa: Vision System

Software for a vision system for a process line. The project enables object detection as well as color and shape recognition (mainly circles) based on camera images. The system can be used for automatic inspection of products on a production line.

## Requirements

- Python 3.x
- OpenCV

## Installation

1. Install the required libraries:
    ```
    pip install numpy python-snap7
    ```

2. Install OpenCV:
On Ubuntu or Debian-based systems, you can install OpenCV using:
    ```
    sudo apt-get install python3-opencv
    ```
    On other systems, you can install it via pip:

    ```
    pip install opencv-python
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

> **Note:**  
> If you see an error like `can't find snap7 shared library`, you need to install the native snap7 library (`libsnap7.so`).  
> On Raspberry Pi or ARM Linux, run:
> ```
> sudo apt update
> sudo apt install git build-essential cmake
> cd /tmp
> git clone https://github.com/gijzelaerr/snap7.git
> cd snap7/build/unix
> make -f arm_v7_linux.mk -j4
> sudo cp ../bin/arm_v7-linux/libsnap7.so /usr/local/lib/
> sudo ldconfig
> ```
> Then try running the command again.

## Configuration
The configuration file `src/config.py` contains parameters for the vision system, such as frame dimensions, margins, and limits for object detection repetitions. You can adjust these parameters to fit your specific use case.

## Authors

Project created as part of work on a vision system for a process line