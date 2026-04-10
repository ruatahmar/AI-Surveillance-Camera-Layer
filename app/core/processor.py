import cv2
import numpy as np
import logging
from queue import Queue
from app.detection.video import VideoStream
from app.detection.person import PersonDetector
from app.idCard.detector import IDCardDetector
from app.core.config import SourceConfig

logger = logging.getLogger(__name__)


class VideoProcessor:
    def __init__(
        self,
        config: SourceConfig,
        model_path: str,
        conf_threshold: float,
        frame_queue: Queue | None = None,
    ) -> None:
        self.config = config
        self.stream = VideoStream()
        self.detector = PersonDetector(conf=conf_threshold)
        self.id_detector = IDCardDetector(model_path=model_path, conf=0.1)
        self.is_running = False
        self.frame_queue = frame_queue

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
        # Detect people
        people = self.detector.detect(frame)

        # *insert loitering logic here*
        if self.config.loitering_enabled:
            pass

        for person in people:
            x1, y1, x2, y2 = person["bbox"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Crop and detect ID card
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            label = self.id_detector.detect(crop)
            cv2.putText(
                frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
            )
        return frame

    def stop(self) -> None:
        self.is_running = False
        self.stream.release()
        logger.info(f"Stopped processing source: {self.config.name}")
