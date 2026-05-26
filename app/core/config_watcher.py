import time
import logging
import threading
from pathlib import Path
from typing import Callable
from app.core.config import Config, ConfigDiff

logger = logging.getLogger(__name__)

OnChangeCallback = Callable[[Config, ConfigDiff], None]


class ConfigWatcher:
    def __init__(
        self,
        config_path: str | Path,
        interval: float = 3.0,
    ) -> None:
        self._path = Path(config_path)
        self._interval = interval
        self._callbacks: list[OnChangeCallback] = []
        self._current_config: Config | None = None
        self._last_mtime: float = 0.0
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def register(self, callback: OnChangeCallback) -> None:
        self._callbacks.append(callback)

    def start(self, initial_config: Config) -> None:
        self._current_config = initial_config
        self._last_mtime = self._get_mtime()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll, name="ConfigWatcher", daemon=True)
        self._thread.start()
        logger.info("ConfigWatcher started (polling every %.1fs)", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self._interval + 1)
        logger.info("ConfigWatcher stopped")

    def _get_mtime(self) -> float:
        try:
            return self._path.stat().st_mtime
        except OSError:
            return 0.0

    def _poll(self) -> None:
        while not self._stop_event.wait(self._interval):
            try:
                mtime = self._get_mtime()
                if mtime == self._last_mtime:
                    continue

                self._last_mtime = mtime
                logger.info("config.toml changed, reloading...")

                new_config = Config.load_from_toml(self._path)
                diff = Config.diff(self._current_config, new_config)  # type: ignore[arg-type]
                self._current_config = new_config

                if diff.restart_required:
                    for reason in diff.restart_required:
                        logger.warning("Restart required: %s", reason)

                for callback in self._callbacks:
                    try:
                        callback(new_config, diff)
                    except Exception:
                        logger.exception("Error in ConfigWatcher callback")

            except Exception:
                logger.exception("Error in ConfigWatcher poll loop")