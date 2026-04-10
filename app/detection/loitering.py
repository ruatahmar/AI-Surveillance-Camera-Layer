import time
from datetime import datetime
from app.core.config import SourceConfig

class LoiteringDetector:
    def __init__(self, config: SourceConfig, threshold: float):
        self.config = config
        self.threshold = threshold
        self.person_timestamps = {}  # track_id -> first_seen_time
        self.alert_counts = {}       # track_id -> count of alerts sent

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

    def update(self, tracked_people: list) -> list[int]:
        """
        Updates tracking and returns list of track_ids that triggered a new loitering alert.
        """
        triggered_alerts = []
        
        if not self._is_in_window():
            # Reset tracking if we are not in a loitering window
            self.person_timestamps.clear()
            self.alert_counts.clear()
            return triggered_alerts

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
            
            # Check threshold and alert limit
            if self.alert_counts[tid] < self.config.alert_limit_per_track:
                duration = now - self.person_timestamps[tid]
                if duration >= self.threshold:
                    triggered_alerts.append(tid)
                    self.alert_counts[tid] += 1

        # Clean up stale track IDs
        stale_ids = set(self.person_timestamps.keys()) - current_ids
        for sid in stale_ids:
            del self.person_timestamps[sid]
            del self.alert_counts[sid]

        return triggered_alerts
