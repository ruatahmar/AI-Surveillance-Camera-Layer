from ultralytics.models.yolo import YOLO
import numpy as np
from typing import TypedDict


class PersonBox(TypedDict):
    bbox: tuple[int, int, int, int]
    confidence: float


class PersonDetector:
    def __init__(self, model_path: str = "yolov8n.pt", conf: float = 0.5) -> None:
        self.model: YOLO = YOLO(model_path)
        self.conf: float = conf

    def detect(self, frame: np.ndarray) -> list[PersonBox]:
        results = self.model(frame, conf=self.conf, classes=[0], verbose=False)
        if not results:
            return []

        boxes: list[PersonBox] = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            boxes.append({"bbox": (x1, y1, x2, y2), "confidence": float(box.conf[0])})
        return boxes
