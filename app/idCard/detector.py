import numpy as np
from ultralytics.models.yolo import YOLO


class IDCardDetector:
    def __init__(
        self, model_path: str = "data/models/best.pt", conf: float = 0.5
    ) -> None:
        self.model: YOLO = YOLO(model_path)
        self.conf: float = conf

    def detect(self, person_crop: np.ndarray) -> str:
        """
        Detects if a person is wearing an ID card.
        Returns 'with_card', 'without_card', or 'no_id' if the detection fails.
        """
        results = self.model(person_crop, conf=self.conf, verbose=False)
        if not results or len(results[0].boxes) == 0:
            return "no_id"

        # Get the detection with the highest confidence (with_card vs without_card)
        box = max(results[0].boxes, key=lambda b: float(b.conf[0]))
        class_id = int(box.cls[0])

        # Return 'with_card' or 'without_card'
        return self.model.names[class_id]
