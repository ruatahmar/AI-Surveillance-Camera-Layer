import time


class CrowdMonitor:
    def __init__(self, min_people: int = 5, min_duration: float = 15):
        self.min_people = min_people
        self.min_duration = min_duration

        self.start_time = None
        self.alert_triggered = False

    def update(self, people_count: int) -> bool:
        now = time.time()

        if people_count >= self.min_people:
            if self.start_time is None:
                self.start_time = now

            if (now - self.start_time) >= self.min_duration:
                if not self.alert_triggered:
                    self.alert_triggered = True
                    return True
        else:
            self.start_time = None
            self.alert_triggered = False

        return False
