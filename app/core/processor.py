import cv2
import numpy as np
import logging
from queue import Queue
from app.detection.video import VideoStream
from app.detection.person import PersonDetector
from app.idCard.detector import IDCardDetector
from app.detection.loitering import LoiteringDetector
from app.detection.crowd_detection import CrowdMonitor
from app.core.config import SourceConfig
from app.utils.alerts import send_alert

logger = logging.getLogger(__name__)


class VideoProcessor:
    def __init__(
        self,
        config: SourceConfig,
        model_path: str,
        conf_threshold: float,
        loitering_threshold: float,  # Pass global default
        frame_queue: Queue | None = None,
    ) -> None:
        self.config = config
        self.stream = VideoStream()
        self.detector = PersonDetector(conf=conf_threshold)
        self.id_detector = IDCardDetector(model_path=model_path, conf=0.1)
        
        # Use source threshold if provided, else global
        threshold = config.loitering_threshold if config.loitering_threshold is not None else loitering_threshold
        self.loitering_detector = LoiteringDetector(config=config, threshold=threshold)
        
        self.crowd_monitor = CrowdMonitor()
        self.is_running = False
        self.frame_queue = frame_queue
        # track_id -> count of no_id alerts sent
        self.alerted_no_id_counts = {}

    def start(self) -> None:
        try:
            self.stream.open(self.config.source)
        except Exception as e:
            logger.error(f"Failed to open source {self.config.name}: {e}")
            return

        self.is_running = True
        logger.info(f"Started processing source: {self.config.name}")

        try:
            while self.is_running:
                frame = self.stream.read()
                if frame is None:
                    logger.warning(f"No frame from source: {self.config.name}")
                    break

                # Process the frame
                processed_frame = self.process_frame(frame)

                # Send frame to UI queue if provided
                if self.frame_queue is not None:
                    # If queue is full, drop the oldest frame to stay "live"
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                        except:
                            pass
                    self.frame_queue.put_nowait((self.config.name, processed_frame))

        finally:
            self.stop()

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        # Detect and track people
        people = self.detector.detect(frame)

        # Update Loitering Detector
        loitering_alerts = self.loitering_detector.update(people)
        if loitering_alerts:
            send_alert(self.config.name, "loitering", frame)

        # Update Crowd Monitor
        if self.crowd_monitor.update(len(people)):
            send_alert(self.config.name, "crowd", frame)

        current_track_ids = set()
        for person in people:
            x1, y1, x2, y2 = person["bbox"]
            tid = person.get("track_id")
            if tid is not None:
                current_track_ids.add(tid)
            
            label_color = (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), label_color, 2)

            # Crop and detect ID card
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            label = self.id_detector.detect(crop)
            
            # Alert for "no_id" if we haven't hit the limit for this person yet
            if label == "no_id" and tid is not None:
                if tid not in self.alerted_no_id_counts:
                    self.alerted_no_id_counts[tid] = 0
                
                if self.alerted_no_id_counts[tid] < self.config.alert_limit_per_track:
                    send_alert(self.config.name, "no_id", frame)
                    self.alerted_no_id_counts[tid] += 1

            display_label = f"{label} (ID:{tid})" if tid is not None else label
            cv2.putText(
                frame,
                display_label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                label_color,
                2,
            )
        
        # Clean up alerted_no_id_counts for people who left the frame
        stale_ids = set(self.alerted_no_id_counts.keys()) - current_track_ids
        for sid in stale_ids:
            del self.alerted_no_id_counts[sid]
        
        return frame

    def stop(self) -> None:
        self.is_running = False
        self.stream.release()
        logger.info(f"Stopped processing source: {self.config.name}")
