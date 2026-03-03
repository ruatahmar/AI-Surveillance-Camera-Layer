from ultralytics import YOLO


class PersonDetector:
    def __init__(self, model_path="yolov8n.pt", conf=0.5):
        self.model = YOLO(model_path)
        self.conf = conf

    def detect(self, frame) -> list[dict]:
        results = self.model(frame, conf=self.conf, classes=[0], verbose=False)[0]
        boxes = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            boxes.append({"bbox": (x1, y1, x2, y2), "confidence": float(box.conf[0])})
        return boxes
