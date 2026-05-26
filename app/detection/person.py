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

    def reset_tracker(self) -> None:
        if hasattr(self.model, "predictor") and self.model.predictor is not None:
            self.model.predictor.trackers = None

    def detect(self, frame: np.ndarray) -> list[PersonBox]:
        results = self.model.track(
            frame, persist=True, conf=self.conf, classes=[0], verbose=False
        )
        if self._has_tracking_ids(results):
            return self._parse_tracked_results(results)
        return self._detect_fallback(frame)

    def _has_tracking_ids(self, results) -> bool:
        return (
            results
            and results[0].boxes is not None
            and len(results[0].boxes) > 0
            and results[0].boxes.id is not None
        )

    def _parse_tracked_results(self, results) -> list[PersonBox]:
        track_ids = results[0].boxes.id.int().cpu().tolist()
        return [self._box_to_dict(box, tid) for box, tid in zip(results[0].boxes, track_ids)]

    def _detect_fallback(self, frame: np.ndarray) -> list[PersonBox]:
        results = self.model(frame, conf=self.conf, classes=[0], verbose=False)
        if not results or len(results[0].boxes) == 0:
            return []
        return [self._box_to_dict(box, None) for box in results[0].boxes]

    def _box_to_dict(self, box, track_id: int | None) -> PersonBox:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        return {
            "bbox": (x1, y1, x2, y2),
            "confidence": float(box.conf[0]),
            "track_id": track_id,
        }
