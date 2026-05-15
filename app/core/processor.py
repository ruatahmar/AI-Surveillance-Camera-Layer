import time
import logging
from queue import Queue
import numpy as np
from app.detection.video import VideoStream
from app.detection.person import PersonDetector
from app.idCard.detector import IDCardDetector
from app.detection.loitering import LoiteringDetector
from app.detection.crowd_detection import CrowdMonitor
from app.core.config import SourceConfig
from app.utils.alerts import send_alert
from app.utils.drawing import draw_people

logger = logging.getLogger(__name__)


class VideoProcessor:
    def __init__(
        self,
        config: SourceConfig,
        model_path: str,
        conf_threshold: float,
        loitering_threshold: float,
        frame_queue: Queue | None = None,
    ) -> None:
        self.config = config
        self.stream = VideoStream()
        self.detector = PersonDetector(conf=conf_threshold)
        self.id_detector = IDCardDetector(model_path=model_path, conf=0.1)

        threshold = config.loitering_threshold if config.loitering_threshold is not None else loitering_threshold
        self.loitering_detector = LoiteringDetector(config=config, threshold=threshold)

        self.crowd_monitor = CrowdMonitor(
            min_people=config.crowd_min_people,
            min_duration=config.crowd_min_duration,
        )
        self.is_running = False
        self.frame_queue = frame_queue
        self.alerted_no_id_counts: dict[int, int] = {}
        self._last_people: list[dict] = []
        self._frame_count = 0
        self._last_reset_time = time.time()

    def start(self) -> None:
        try:
            self.stream.open(self.config.source)
        except Exception as e:
            logger.error(f"Failed to open source {self.config.name}: {e}")
            return

        self.is_running = True
        logger.info(f"Started processing source: {self.config.name}")

        skip = self.config.process_every_n_frames
        reset_interval = self.config.tracker_reset_interval

        try:
            while self.is_running:
                frame = self.stream.read()
                if frame is None:
                    logger.warning(f"No frame from source: {self.config.name}")
                    break

                self._frame_count += 1
                should_process = (self._frame_count % skip == 0)

                if should_process:
                    processed_frame = self.process_frame(frame)

                    if reset_interval > 0:
                        now = time.time()
                        if now - self._last_reset_time >= reset_interval:
                            logger.info(f"Tracker reset after {reset_interval}s on {self.config.name}")
                            self.detector.reset_tracker()
                            self._last_people = []
                            self.alerted_no_id_counts.clear()
                            self.loitering_detector.reset()
                            self._last_reset_time = now
                else:
                    processed_frame = draw_people(frame.copy(), self._last_people)

                if self.frame_queue is not None:
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                        except:
                            pass
                    self.frame_queue.put_nowait((self.config.name, processed_frame))

        finally:
            self.stop()

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        people = self.detector.detect(frame)

        loitering_ids = self.loitering_detector.update(people)
        if loitering_ids:
            send_alert(self.config.name, "loitering", frame)

        if self.crowd_monitor.update(len(people)):
            send_alert(self.config.name, "crowd", frame)

        current_track_ids = set()
        for person in people:
            x1, y1, x2, y2 = person["bbox"]
            tid = person.get("track_id")
            if tid is not None:
                current_track_ids.add(tid)

            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                person["label"] = "person"
                continue

            label = self.id_detector.detect(crop)
            person["label"] = label

            if label == "no_id" and tid is not None:
                if tid not in self.alerted_no_id_counts:
                    self.alerted_no_id_counts[tid] = 0
                if self.alerted_no_id_counts[tid] < self.config.alert_limit_per_track:
                    send_alert(self.config.name, "no_id", frame)
                    self.alerted_no_id_counts[tid] += 1

        draw_people(frame, people)

        stale_ids = set(self.alerted_no_id_counts.keys()) - current_track_ids
        for sid in stale_ids:
            del self.alerted_no_id_counts[sid]

        self._last_people = people
        return frame

    def stop(self) -> None:
        self.is_running = False
        self.stream.release()
        logger.info(f"Stopped processing source: {self.config.name}")
