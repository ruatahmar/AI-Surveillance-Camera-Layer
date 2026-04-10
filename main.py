import argparse
import logging
import threading
import cv2
import queue
from pathlib import Path
from app.core.config import Config
from app.core.processor import VideoProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
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
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {args.config}")
        return

    try:
        current_settings = Config.load_from_toml(config_path)
        logger.info(f"Loaded config from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    logger.info(f"Starting AI Surveillance Camera Layer (Headless: {args.headless})")
    logger.info(f"Loaded config with {len(current_settings.sources)} sources")

    # Shared queue for frames (main thread consumes, processor threads produce)
    # We use a small maxsize to ensure we only show the latest frames
    frame_queue = (
        queue.Queue(maxsize=len(current_settings.sources) * 2)
        if not args.headless
        else None
    )

    processors: list[VideoProcessor] = []
    threads: list[threading.Thread] = []

    for source_config in current_settings.sources:
        processor = VideoProcessor(
            config=source_config,
            model_path=current_settings.general.model_path,
            conf_threshold=current_settings.general.conf_threshold,
            loitering_threshold=current_settings.general.loitering_threshold,
            frame_queue=frame_queue,
        )
        processors.append(processor)

        thread = threading.Thread(target=processor.start, name=source_config.name)
        thread.daemon = True
        thread.start()
        threads.append(thread)

    try:
        while any(t.is_alive() for t in threads):
            if not args.headless and frame_queue is not None:
                try:
                    # Try to get a frame from any source
                    source_name, frame = frame_queue.get(timeout=0.1)
                    cv2.imshow(f"Source: {source_name}", frame)
                except queue.Empty:
                    pass

                # Check for exit key in the main thread
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    logger.info("Exit requested via 'q' key")
                    break
            else:
                # In headless mode, just wait
                for t in threads:
                    t.join(timeout=0.1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested via KeyboardInterrupt")
    finally:
        logger.info("Cleaning up...")
        for processor in processors:
            processor.stop()
        if not args.headless:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
