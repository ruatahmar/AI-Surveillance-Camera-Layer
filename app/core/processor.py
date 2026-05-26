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
        self._recent_no_id_alerts: list[tuple[float, float, float]] = []
        self._last_people: list[dict] = []
        self._frame_count = 0
        self._last_reset_time = time.time()

    def start(self) -> None:
        if not self._open_stream():
            return

        self.is_running = True
        logger.info(f"Started processing source: {self.config.name}")

        try:
            while self.is_running:
                try:
                    frame = self._read_frame()
                    if frame is None:
                        break

                    processed = self._process_or_draw(frame)
                    self._check_tracker_reset()
                    self._push_to_queue(processed)
                except Exception:
                    logger.exception("Error processing frame")

        finally:
            self.stop()

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        people = self.detector.detect(frame)
        self._label_people(frame, people)
        self._handle_alerts(people, frame)
        self._annotate_and_cache(frame, people)
        return frame

    def stop(self) -> None:
        self.is_running = False
        self.stream.release()
        logger.info(f"Stopped processing source: {self.config.name}")

    def _open_stream(self) -> bool:
        try:
            self.stream.open(self.config.source)
            return True
        except Exception as e:
            logger.error(f"Failed to open source {self.config.name}: {e}")
            return False

    def _read_frame(self) -> np.ndarray | None:
        frame = self.stream.read()
        if frame is None:
            logger.warning(f"No frame from source: {self.config.name}")
        return frame

    def _process_or_draw(self, frame: np.ndarray) -> np.ndarray:
        self._frame_count += 1
        if self._frame_count % self.config.process_every_n_frames == 0:
            return self.process_frame(frame)
        return draw_people(frame.copy(), self._last_people)

    def _check_tracker_reset(self) -> None:
        interval = self.config.tracker_reset_interval
        if interval <= 0:
            return

        now = time.time()
        if now - self._last_reset_time < interval:
            return

        logger.info(f"Tracker reset after {interval}s on {self.config.name}")
        self.detector.reset_tracker()
        self._last_people = []
        self._recent_no_id_alerts.clear()
        self.loitering_detector.reset()
        self._last_reset_time = now

    def _push_to_queue(self, frame: np.ndarray) -> None:
        if self.frame_queue is None:
            return

        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except:
                pass

        self.frame_queue.put_nowait((self.config.name, frame))

    def _label_people(self, frame: np.ndarray, people: list) -> None:
        for person in people:
            x1, y1, x2, y2 = person["bbox"]
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                person["label"] = "person"
                continue
            person["label"] = self.id_detector.detect(crop)

    def _handle_alerts(self, people: list, frame: np.ndarray) -> None:
        self._handle_loitering(people, frame)
        self._handle_crowd(people, frame)
        self._handle_no_id(people, frame)

    def _handle_loitering(self, people: list, frame: np.ndarray) -> None:
        alerted_ids = self.loitering_detector.update(people)
        if alerted_ids:
            send_alert(self.config.name, "loitering", frame)

    def _handle_crowd(self, people: list, frame: np.ndarray) -> None:
        if self.crowd_monitor.update(len(people)):
            send_alert(self.config.name, "crowd", frame)

    def _handle_no_id(self, people: list, frame: np.ndarray) -> None:
        now = time.time()
        timeout = self.config.alert_cooldown
        dist = self.config.no_id_alert_distance

        self._recent_no_id_alerts = [
            (cx, cy, ts)
            for cx, cy, ts in self._recent_no_id_alerts
            if now - ts < timeout
        ]

        for person in people:
            if person.get("label") != "no_id":
                continue

            x1, y1, x2, y2 = person["bbox"]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

            already = any(
                ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5 < dist
                for px, py, _ in self._recent_no_id_alerts
            )
            if already:
                continue

            send_alert(self.config.name, "no_id", frame)
            self._recent_no_id_alerts.append((cx, cy, now))

    def _annotate_and_cache(self, frame: np.ndarray, people: list) -> None:
        draw_people(frame, people)
        self._last_people = people
