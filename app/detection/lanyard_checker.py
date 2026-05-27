import cv2
import numpy as np


LOWER_GREEN = np.array([15, 10, 10])
UPPER_GREEN = np.array([100, 255, 255])


def compute_green_mask(crop: np.ndarray) -> np.ndarray:
    if crop.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hsv_green = cv2.inRange(hsv, LOWER_GREEN, UPPER_GREEN)

    b, g, r = cv2.split(crop.astype(np.float32))
    rgb_green = (g >= r) & (g >= b)
    rgb_green = rgb_green.astype(np.uint8) * 255

    green_mask = cv2.bitwise_or(hsv_green, rgb_green)

    # White text on green — count white pixels near green as good
    hsv_white = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 30, 255]))
    green_dilated = cv2.dilate(green_mask, np.ones((5, 5), np.uint8), iterations=1)
    white_near_green = cv2.bitwise_and(hsv_white, green_dilated)

    return cv2.bitwise_or(green_mask, white_near_green)


def green_pixel_ratio(crop: np.ndarray) -> float:
    mask = compute_green_mask(crop)
    if mask.size == 0:
        return 0.0
    return cv2.countNonZero(mask) / (mask.shape[0] * mask.shape[1])


def is_green_lanyard(crop: np.ndarray, threshold: float = 0.08) -> bool:
    return green_pixel_ratio(crop) > threshold
