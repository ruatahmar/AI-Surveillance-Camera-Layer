from ultralytics.models.yolo import YOLO
import numpy as np
from typing import TypedDict, Optional


class PoseKeypoints(TypedDict):
    nose: Optional[tuple[int, int]]
    left_shoulder: Optional[tuple[int, int]]
    right_shoulder: Optional[tuple[int, int]]
    left_eye: Optional[tuple[int, int]]
    right_eye: Optional[tuple[int, int]]


class PoseDetection(TypedDict):
    bbox: tuple[int, int, int, int]
    keypoints: PoseKeypoints
    confidence: float


class PoseDetector:
    def __init__(self, model_path: str = "yolov8n-pose.pt", conf: float = 0.5) -> None:
        self.model: YOLO = YOLO(model_path)
        self.conf: float = conf

    def detect(self, frame: np.ndarray) -> list[PoseDetection]:
        results = self.model(frame, conf=self.conf, verbose=False)
        if not results or not results[0].keypoints:
            return []

        detections: list[PoseDetection] = []
        for i, box in enumerate(results[0].boxes):
            # Get keypoints for this person
            # YOLOv8 pose keypoints: 0: nose, 1: l_eye, 2: r_eye, 3: l_ear, 4: r_ear, 
            # 5: l_shoulder, 6: r_shoulder...
            kp = results[0].keypoints.xy[i].cpu().numpy()
            
            # Helper to get (x, y) if confidence is high enough (non-zero)
            def get_kp(idx):
                if idx < len(kp) and np.any(kp[idx]):
                    return (int(kp[idx][0]), int(kp[idx][1]))
                return None

            pose_kp: PoseKeypoints = {
                "nose": get_kp(0),
                "left_eye": get_kp(1),
                "right_eye": get_kp(2),
                "left_shoulder": get_kp(5),
                "right_shoulder": get_kp(6),
            }

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detections.append({
                "bbox": (x1, y1, x2, y2),
                "keypoints": pose_kp,
                "confidence": float(box.conf[0])
            })
            
        return detections
