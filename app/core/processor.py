import os
import time
import logging
from pathlib import Path
from queue import Queue
import cv2
import numpy as np
from app.detection.video import VideoStream
from app.detection.person import PersonDetector
from app.idCard.detector import IDCardDetector
from app.detection.loitering import LoiteringDetector
from app.detection.crowd_detection import CrowdMonitor
from app.detection.lanyard_checker import compute_green_mask, green_pixel_ratio, is_green_lanyard
from app.core.config import SourceConfig, EmailConfig
from app.utils.alerts import send_alert
from app.utils.drawing import draw_people
from app.notification.email import should_send_email, send_alert_email

logger = logging.getLogger(__name__)


class VideoProcessor:
    def __init__(
        self,
        config: SourceConfig,
        model_path: str,
        conf_threshold: float,
        loitering_threshold: float,
        frame_queue: Queue | None = None,
        email_config: EmailConfig | None = None,
    ) -> None:
        self.config = config
        self.email_config = email_config or EmailConfig()
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
        self._alert_counts: dict[int, int] = {}
        self._last_people: list[dict] = []
        self._frame_count = 0
        self._last_reset_time = time.time()
        self._debug = os.getenv("APP_ENV") == "dev"
        self._debug_dir = Path("debug")
        self._debug_save_count = 0
        self._debug_save_max = 20
        self._debug_frame_interval = 3
        self._last_debug_save_frame = 0

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
        self._save_debug_frame(frame, people)
        return frame

    def _save_debug_frame(self, frame: np.ndarray, people: list) -> None:
        if not self._debug:
            return
        if self._debug_save_count >= self._debug_save_max:
            return
        if self._frame_count - self._last_debug_save_frame < self._debug_frame_interval:
            return

        has_lanyard = any(
            p.get("id_label") == "Lanyard" for p in people
        )
        if not has_lanyard:
            return

        self._debug_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = self._debug_dir / f"frame_{ts}_{self._frame_count:06d}.jpg"
        cv2.imwrite(str(path), frame)
        self._debug_save_count += 1
        self._last_debug_save_frame = self._frame_count
        logger.debug("Saved debug frame %s", path)

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
        self._alert_counts.clear()
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

            result = self.id_detector.detect(crop)
            label = result["label"]
            id_bbox = result["bbox"]
            id_conf = result.get("confidence")

            if self._debug:
                person["id_label"] = label
                person["id_conf"] = id_conf

            if label == "Cards":
                person["label"] = "person"
            elif label == "no_id":
                person["label"] = "no_id"
            elif label == "Lanyard" and id_bbox is not None and self.config.green_lanyard_enabled:
                lx1, ly1, lx2, ly2 = id_bbox
                strap_crop = crop[ly1:ly2, lx1:lx2]
                if strap_crop.size > 0:
                    ratio = green_pixel_ratio(strap_crop)
                    is_green = ratio > self.config.lanyard_green_threshold
                    if self._debug:
                        person["green_ratio"] = ratio
                        mask = compute_green_mask(strap_crop)
                        person["green_mask_overlay"] = (mask, x1 + lx1, y1 + ly1)
                        logger.info(
                            "lanyard=%s strap_crop=%s green_ratio=%.3f threshold=%.2f",
                            self.config.name, strap_crop.shape, ratio,
                            self.config.lanyard_green_threshold,
                        )
                    if is_green:
                        person["label"] = "green_lanyard"
                    else:
                        person["label"] = "wrong_lanyard"
                else:
                    person["label"] = "wrong_lanyard"
            else:
                person["label"] = label

    def _handle_alerts(self, people: list, frame: np.ndarray) -> None:
        self._handle_loitering(people, frame)
        self._handle_crowd(people, frame)
        self._handle_id_alerts(people, frame)

    def _maybe_email(self, alert_type: str) -> None:
        if should_send_email(self.email_config, alert_type):
            send_alert_email(self.email_config, self.config.name, alert_type)

    def _handle_loitering(self, people: list, frame: np.ndarray) -> None:
        alerted_ids = self.loitering_detector.update(people)
        if alerted_ids:
            send_alert(self.config.name, "loitering", frame)
            self._maybe_email("loitering")

    def _handle_crowd(self, people: list, frame: np.ndarray) -> None:
        if self.crowd_monitor.update(len(people)):
            send_alert(self.config.name, "crowd", frame)
            self._maybe_email("crowd")

    def _handle_id_alerts(self, people: list, frame: np.ndarray) -> None:
        now = time.time()
        timeout = self.config.alert_cooldown
        dist = self.config.no_id_alert_distance
        confirm = self.config.alert_confirm_frames

        self._recent_no_id_alerts = [
            (cx, cy, ts)
            for cx, cy, ts in self._recent_no_id_alerts
            if now - ts < timeout
        ]

        current_ids = set()

        for person in people:
            tid = person.get("track_id")
            if tid is None:
                continue
            current_ids.add(tid)

            label = person.get("label")
            if label == "no_id":
                alert_type = "no_id"
            elif label == "wrong_lanyard":
                alert_type = "wrong_lanyard"
            elif label == "green_lanyard":
                alert_type = "green_lanyard"
            else:
                self._alert_counts.pop(tid, None)
                continue

            count = self._alert_counts.get(tid, 0) + 1
            self._alert_counts[tid] = count

            if count < confirm:
                continue

            x1, y1, x2, y2 = person["bbox"]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

            already = any(
                ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5 < dist
                for px, py, _ in self._recent_no_id_alerts
            )
            if already:
                continue

            send_alert(self.config.name, alert_type, frame)
            self._maybe_email(alert_type)
            self._recent_no_id_alerts.append((cx, cy, now))

        stale = [tid for tid in self._alert_counts if tid not in current_ids]
        for tid in stale:
            del self._alert_counts[tid]

    def apply_tunable(self, source_config: SourceConfig, general_conf_threshold: float | None = None, general_loitering_threshold: float | None = None, email_config: EmailConfig | None = None) -> None:
        """Apply tunable config changes in-place without restarting the processor."""
        self.config = source_config
        if email_config is not None:
            self.email_config = email_config

        # Update detector confidence threshold
        if general_conf_threshold is not None:
            self.detector.model.conf = general_conf_threshold

        # Update loitering threshold
        effective_threshold = (
            source_config.loitering_threshold
            if source_config.loitering_threshold is not None
            else (general_loitering_threshold or self.loitering_detector.threshold)
        )
        self.loitering_detector.threshold = effective_threshold
        self.loitering_detector.config = source_config

        # Update crowd monitor params
        self.crowd_monitor.min_people = source_config.crowd_min_people
        self.crowd_monitor.min_duration = source_config.crowd_min_duration

        logger.info("Applied tunable config update to source: %s", source_config.name)

    def _annotate_and_cache(self, frame: np.ndarray, people: list) -> None:
        draw_people(frame, people)
        self._last_people = people