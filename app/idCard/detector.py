import numpy as np
from ultralytics.models.yolo import YOLO


class IDCardDetector:
    def __init__(
        self, model_path: str = "data/models/best.pt", conf: float = 0.5
    ) -> None:
        self.model: YOLO = YOLO(model_path)
        self.conf: float = conf

    def detect(self, person_crop: np.ndarray) -> dict:
        results = self.model(person_crop, conf=self.conf, verbose=False)
        if not results or len(results[0].boxes) == 0:
            return {"label": "no_id", "bbox": None, "confidence": 0.0}

        box = max(results[0].boxes, key=lambda b: float(b.conf[0]))
        class_id = int(box.cls[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        return {
            "label": self.model.names[class_id],
            "bbox": (x1, y1, x2, y2),
            "confidence": float(box.conf[0]),
        }
