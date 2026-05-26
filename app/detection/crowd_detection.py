import time


class CrowdMonitor:
    def __init__(self, min_people: int = 5, min_duration: float = 15):
        self.min_people = min_people
        self.min_duration = min_duration
        self.start_time = None
        self.alert_triggered = False

    def update(self, people_count: int) -> bool:
        if not self._is_count_above_threshold(people_count):
            self._reset()
            return False
        self._ensure_start_time()
        return self._try_trigger()

    def _is_count_above_threshold(self, count: int) -> bool:
        return count >= self.min_people

    def _ensure_start_time(self) -> None:
        if self.start_time is None:
            self.start_time = time.time()

    def _try_trigger(self) -> bool:
        if self.alert_triggered or self.start_time is None:
            return False
        if time.time() - self.start_time < self.min_duration:
            return False
        self.alert_triggered = True
        return True

    def _reset(self) -> None:
        self.start_time = None
        self.alert_triggered = False
