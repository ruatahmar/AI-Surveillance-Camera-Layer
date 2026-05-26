import argparse
import logging
import threading
import cv2
import queue
from pathlib import Path
from app.core.config import Config
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

    try:
        if args.headless:
            _headless_wait(threads)
        else:
            _display_loop(frame_queue, threads)
    except KeyboardInterrupt:
        logger.info("Shutdown requested via KeyboardInterrupt")
    finally:
        _cleanup(processors, not args.headless)


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
