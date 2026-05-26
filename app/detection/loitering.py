import time
from datetime import datetime
from app.core.config import SourceConfig

class LoiteringDetector:
    def __init__(self, config: SourceConfig, threshold: float):
        self.config = config
        self.threshold = threshold
        self.person_timestamps = {}  # track_id -> first_seen_time
        self.alert_counts = {}       # track_id -> count of alerts sent
        self.last_alert_time = {}    # track_id -> last alert timestamp

    def _is_in_window(self) -> bool:
        if not self.config.loitering_enabled:
            return False
        
        now = datetime.now().time()
        for window in self.config.loitering_windows:
            try:
                start = datetime.strptime(window.start, "%H:%M").time()
                end = datetime.strptime(window.end, "%H:%M").time()
                
                if start <= end:
                    if start <= now <= end:
                        return True
                else:  # overnight window
                    if now >= start or now <= end:
                        return True
            except ValueError:
                continue
        return False

    def reset(self) -> None:
        self.person_timestamps.clear()
        self.alert_counts.clear()
        self.last_alert_time.clear()

    def update(self, tracked_people: list) -> list[int]:
        if not self._is_in_window():
            self.reset()
            return []

        current_ids = self._collect_current_ids(tracked_people)
        now = time.time()

        triggered = [
            tid
            for tid in current_ids
            if self._should_alert(tid, now)
        ]

        for tid in triggered:
            self.alert_counts[tid] += 1
            self.last_alert_time[tid] = now

        self._cleanup_stale(current_ids)
        return triggered

    def _collect_current_ids(self, tracked_people: list) -> set:
        current_ids = set()
        now = time.time()

        for person in tracked_people:
            tid = person.get("track_id")
            if tid is None:
                continue
            current_ids.add(tid)

            if tid not in self.person_timestamps:
                self.person_timestamps[tid] = now
                self.alert_counts[tid] = 0

        return current_ids

    def _should_alert(self, tid: int, now: float) -> bool:
        if self.alert_counts[tid] >= self.config.loitering_alert_limit:
            return False

        duration = now - self.person_timestamps[tid]
        if duration < self.threshold:
            return False

        last_alert = self.last_alert_time.get(tid, 0.0)
        if now - last_alert < self.config.alert_cooldown:
            return False

        return True

    def _cleanup_stale(self, current_ids: set) -> None:
        stale_ids = set(self.person_timestamps) - current_ids
        for sid in stale_ids:
            del self.person_timestamps[sid]
            del self.alert_counts[sid]
            self.last_alert_time.pop(sid, None)
