# app/camera.py
import cv2 as cv
import threading, asyncio, os

os.environ["LIBCAMERA_LOG_LEVELS"] = (
    "*:2"  # Ustawienie poziomu logowania dla libcamera, aby uniknąć nadmiaru informacji w konsoli
)

try:
    from picamera2 import Picamera2  # type: ignore

    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False


class Camera:
    def __init__(self, width=640, height=360, fps=30):
        self.lock = threading.Lock()
        self.frame: bytes | None = None
        self.running = True
        self._released = False
        self.boundary = b"frame"

        if PICAMERA_AVAILABLE:
            self.backend = "picamera2"
            self.cam = Picamera2()
            self.cam.configure(
                self.cam.create_preview_configuration(main={"size": (width, height)})
            )
            self.cam.start()
            self._get_frame = lambda: cv.cvtColor(
                self.cam.capture_array(), cv.COLOR_RGB2BGR
            )
            self._release_backend = self.cam.stop
        else:
            self.backend = "opencv"
            self.cam = cv.VideoCapture(0)
            self.cam.set(cv.CAP_PROP_FRAME_WIDTH, width)
            self.cam.set(cv.CAP_PROP_FRAME_HEIGHT, height)
            self.cam.set(cv.CAP_PROP_FPS, fps)
            if not self.cam.isOpened():
                raise RuntimeError("Cannot open camera")
            self._get_frame = lambda: self.cam.read()[1]
            self._release_backend = self.cam.release

        # Background reader keeps latest frame ready for MJPEG streaming.
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def get_frame(self):
        with self.lock:
            return self._get_frame()

    def _reader(self):
        while self.running:
            with self.lock:
                frame = self._get_frame()
            if frame is None:
                continue
            ok, jpg = cv.imencode(".jpg", frame, [int(cv.IMWRITE_JPEG_QUALITY), 70])
            if not ok:
                continue
            # with self.lock:
            self.frame = jpg.tobytes()

    def release(self):
        print("Releasing camera...")
        if self._released:
            return
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1)
        with self.lock:
            self._release_backend()
        self._released = True

    async def mjpeg_generator(self):
        while self.running:
            await asyncio.sleep(0.03)
            data = self.frame
            if not data:
                continue
            yield (
                b"--" + self.boundary + b"\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: "
                + str(len(data)).encode()
                + b"\r\n\r\n"
                + data
                + b"\r\n"
            )

    def stop(self):
        self.release()
