import cv2
import base64
import requests
import logging
import numpy as np

logger = logging.getLogger(__name__)


def send_alert(
    camera_name: str,
    label: str,
    frame: np.ndarray | None = None,
    api_url: str = "http://localhost:3000/api/alerts",
) -> None:
    frame_b64 = _encode_frame(frame)
    payload = {"camera": camera_name, "label": label, "frame": frame_b64}
    _post_alert(api_url, payload)


def _encode_frame(frame: np.ndarray | None) -> str:
    if frame is None:
        return ""
    try:
        _, buffer = cv2.imencode(".jpg", frame)
        return base64.b64encode(buffer).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to encode frame for alert: {e}")
        return ""


def _post_alert(api_url: str, payload: dict) -> None:
    try:
        response = requests.post(api_url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info(f"Successfully sent alert: {payload.get('label')} from {payload.get('camera')}")
        else:
            logger.warning(f"Failed to send alert: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error sending alert to {api_url}: {e}")
