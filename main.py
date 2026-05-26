import argparse
import logging
import threading
import cv2
import queue
from pathlib import Path
from app.core.config import Config, ConfigDiff
from app.core.config_watcher import ConfigWatcher
from app.core.processor import VideoProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    args = _parse_args()
    settings = _load_config(args.config)
    if settings is None:
        return

    frame_queue = _create_queue(settings, args.headless)
    processors, threads = _start_processors(settings, frame_queue)

    watcher = ConfigWatcher(config_path=args.config)
    watcher.register(_make_on_config_change(processors))
    watcher.start(settings)

    try:
        if args.headless:
            _headless_wait(threads)
        else:
            _display_loop(frame_queue, threads)
    except KeyboardInterrupt:
        logger.info("Shutdown requested via KeyboardInterrupt")
    finally:
        watcher.stop()
        _cleanup(processors, not args.headless)


def _make_on_config_change(
    processors: list[VideoProcessor],
) -> object:
    def on_config_change(new_config: Config, diff: ConfigDiff) -> None:
        if diff.restart_required:
            for reason in diff.restart_required:
                logger.warning("Restart required for change to take effect: %s", reason)

        if not diff.tunable:
            return

        # Apply general tunable changes
        general_tunable = diff.tunable.get("__general__", {})
        new_conf_threshold = general_tunable.get("conf_threshold")
        new_loitering_threshold = general_tunable.get("loitering_threshold")

        # Index new sources by name for fast lookup
        new_sources = {s.name: s for s in new_config.sources}

        for processor in processors:
            name = processor.config.name
            if name not in new_sources:
                continue

            # Only call apply_tunable if this source or general tunables changed
            has_source_changes = name in diff.tunable
            has_general_changes = bool(general_tunable)

            if has_source_changes or has_general_changes:
                processor.apply_tunable(
                    source_config=new_sources[name],
                    general_conf_threshold=new_conf_threshold,
                    general_loitering_threshold=new_loitering_threshold,
                )

    return on_config_change


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Surveillance Camera Layer")
    parser.add_argument(
        "--config",
        type=str,
        default="config.toml",
        help="Path to the TOML config file (default: config.toml)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without displaying video windows",
    )
    return parser.parse_args()


def _load_config(config_path_str: str) -> Config | None:
    config_path = Path(config_path_str)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path_str}")
        return None
    try:
        settings = Config.load_from_toml(config_path)
        logger.info(f"Loaded config from {config_path_str}")
        logger.info(f"Loaded config with {len(settings.sources)} sources")
        return settings
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None


def _create_queue(settings: Config, headless: bool) -> queue.Queue | None:
    if headless:
        return None
    return queue.Queue(maxsize=len(settings.sources) * 2)


def _start_processors(
    settings: Config, frame_queue: queue.Queue | None
) -> tuple[list[VideoProcessor], list[threading.Thread]]:
    processors: list[VideoProcessor] = []
    threads: list[threading.Thread] = []

    for source_config in settings.sources:
        processor = VideoProcessor(
            config=source_config,
            model_path=settings.general.model_path,
            conf_threshold=settings.general.conf_threshold,
            loitering_threshold=settings.general.loitering_threshold,
            frame_queue=frame_queue,
        )
        processors.append(processor)

        thread = threading.Thread(target=processor.start, name=source_config.name)
        thread.daemon = True
        thread.start()
        threads.append(thread)

    return processors, threads


def _display_loop(
    frame_queue: queue.Queue, threads: list[threading.Thread]
) -> None:
    while any(t.is_alive() for t in threads):
        try:
            source_name, frame = frame_queue.get(timeout=0.1)
            cv2.imshow(f"Source: {source_name}", frame)
        except queue.Empty:
            pass

        if cv2.waitKey(1) & 0xFF == ord("q"):
            logger.info("Exit requested via 'q' key")
            break


def _headless_wait(threads: list[threading.Thread]) -> None:
    while any(t.is_alive() for t in threads):
        for t in threads:
            t.join(timeout=0.1)


def _cleanup(processors: list[VideoProcessor], has_display: bool) -> None:
    logger.info("Cleaning up...")
    for processor in processors:
        processor.stop()
    if has_display:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()