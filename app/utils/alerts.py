import cv2
import base64
import requests
import logging
import numpy as np

logger = logging.getLogger(__name__)

def send_alert(camera_name: str, label: str, frame: np.ndarray | None = None, api_url: str = "http://localhost:3000/api/alerts"):
    """
    Sends an alert to the frontend API.
    """
    frame_b64 = ""
    if frame is not None:
        try:
            _, buffer = cv2.imencode(".jpg", frame)
            frame_b64 = base64.b64encode(buffer).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encode frame for alert: {e}")

    payload = {
        "camera": camera_name,
        "label": label,
        "frame": frame_b64
    }

    try:
        response = requests.post(api_url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info(f"Successfully sent alert: {label} from {camera_name}")
        else:
            logger.warning(f"Failed to send alert: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error sending alert to {api_url}: {e}")
