import cv2
import numpy as np
from ultralytics.models.yolo import YOLO
from typing import Literal


class IDCardDetector:
    def __init__(
        self, model_path: str = "data/models/best.pt", conf: float = 0.5
    ) -> None:
        self.model: YOLO = YOLO(model_path)
        self.conf: float = conf

    def detect(self, person_crop: np.ndarray) -> str:
        results = self.model(person_crop, conf=self.conf, verbose=False)
        if not results:
            return "no_id"

        boxes = results[0].boxes
        print(f"boxes found: {len(boxes)}")
        if len(boxes) == 0:
            return "no_id"

        box = max(boxes, key=lambda b: float(b.conf[0]))
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        id_crop: np.ndarray = person_crop[y1:y2, x1:x2]

        return self._classify_strap(id_crop)

    def _classify_strap(
        self, id_crop: np.ndarray
    ) -> Literal["student", "teacher", "unknown"]:
        hsv: np.ndarray = cv2.cvtColor(id_crop, cv2.COLOR_BGR2HSV)

        green_mask: np.ndarray = cv2.inRange(
            hsv, np.array([35, 50, 30]), np.array([85, 255, 255])
        )

        red_mask: np.ndarray = cv2.inRange(
            hsv, np.array([0, 50, 30]), np.array([15, 255, 255])
        ) | cv2.inRange(hsv, np.array([165, 50, 30]), np.array([180, 255, 255]))

        green_pixels: int = cv2.countNonZero(green_mask)
        red_pixels: int = cv2.countNonZero(red_mask)

        if green_pixels > red_pixels:
            return "student"
        elif red_pixels > green_pixels:
            return "teacher"
        else:
            return "unknown"
