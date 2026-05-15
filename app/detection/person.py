from ultralytics.models.yolo import YOLO
import numpy as np
from typing import TypedDict


class PersonBox(TypedDict):
    bbox: tuple[int, int, int, int]
    confidence: float
    track_id: int | None


class PersonDetector:
    def __init__(self, model_path: str = "yolov8n.pt", conf: float = 0.5) -> None:
        self.model: YOLO = YOLO(model_path)
        self.conf: float = conf

    def detect(self, frame: np.ndarray) -> list[PersonBox]:
        results = self.model.track(
            frame, persist=True, conf=self.conf, classes=[0], verbose=False
        )
        if not results or results[0].boxes is None or len(results[0].boxes) == 0 or results[0].boxes.id is None:
            # Fallback to normal detection if tracking IDs are not available
            results = self.model(frame, conf=self.conf, classes=[0], verbose=False)
            if not results or len(results[0].boxes) == 0:
                return []
            
            boxes: list[PersonBox] = []
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes.append(
                    {
                        "bbox": (x1, y1, x2, y2),
                        "confidence": float(box.conf[0]),
                        "track_id": None,
                    }
                )
            return boxes

        boxes: list[PersonBox] = []
        track_ids = results[0].boxes.id.int().cpu().tolist()
        for box, tid in zip(results[0].boxes, track_ids):
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            boxes.append(
                {
                    "bbox": (x1, y1, x2, y2),
                    "confidence": float(box.conf[0]),
                    "track_id": tid,
                }
            )
        return boxes
