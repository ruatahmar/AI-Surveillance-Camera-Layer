import cv2
import numpy as np


# this basically helps get cctv footage
class VideoStream:
    def __init__(self) -> None:
        self.cap: cv2.VideoCapture | None = None

    def open(self, source: int | str = 0) -> None:
        """
        (can't be arsed to do a full doc string but can be arsed to write this line.)
        params:
            source (int | str):
                - int: Camera idx (0 is generally the Webcam)
                - str: Path or stream URL (file, RTSP, device path)
        """
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {source}")

        print(f"info: Opened source: {source}")

    def read(self) -> np.ndarray | None:
        if self.cap is None:
            raise RuntimeError("Stream Not Opened")

        ret, frame = self.cap.read()  # this gets the next frame
        return frame if ret else None

    def release(self) -> None:
        if self.cap:
            self.cap.release()
