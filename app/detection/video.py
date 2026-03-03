import cv2


# this basically helps get cctv footage
class VideoStream:
    def __init__(self, source=0):
        # for cctv cams you pass RTSP stream url to source
        # otherwise for webcams and stuff its usually just 0
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {source}")

    def read(self):
        ret, frame = self.cap.read()  # this gets the next frame
        return frame if ret else None

    def release(self):
        self.cap.release()
