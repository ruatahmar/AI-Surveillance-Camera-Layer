import cv2
import numpy as np
from ultralytics import YOLO


class IDCardDetector:
    def __init__(self, model_path="data/models/best.pt", conf=0.5):
        self.model = YOLO(model_path)
        self.conf = conf

    def detect(self, person_crop):
        results = self.model(person_crop, conf=self.conf, verbose=False)[0]
        print(f"boxes found: {len(results.boxes)}")
        if len(results.boxes) == 0:
            return "no_id"

        box = max(results.boxes, key=lambda b: float(b.conf[0]))
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        id_crop = person_crop[y1:y2, x1:x2]

        return self._classify_strap(id_crop)

    def _classify_strap(self, id_crop):
        hsv = cv2.cvtColor(id_crop, cv2.COLOR_BGR2HSV)

        green_mask = cv2.inRange(hsv, np.array([40, 50, 50]), np.array([80, 255, 255]))

        red_mask = cv2.inRange(
            hsv, np.array([0, 50, 50]), np.array([10, 255, 255])
        ) | cv2.inRange(hsv, np.array([170, 50, 50]), np.array([180, 255, 255]))

        green_pixels = cv2.countNonZero(green_mask)
        red_pixels = cv2.countNonZero(red_mask)

        if green_pixels > red_pixels:
            return "student"
        elif red_pixels > green_pixels:
            return "teacher"
        else:
            return "unknown"
