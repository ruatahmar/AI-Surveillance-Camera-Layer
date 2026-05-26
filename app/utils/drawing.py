import cv2
import numpy as np
import os

GOOD_LABELS = {"green_lanyard"}
BAD_LABELS = {"no_id", "wrong_lanyard"}

_DEBUG = os.getenv("APP_ENV") == "dev"


def draw_people(frame: np.ndarray, people: list[dict]) -> np.ndarray:
    for person in people:
        x1, y1, x2, y2 = person["bbox"]
        tid = person.get("track_id")
        label = person.get("label", "person")

        if label in BAD_LABELS:
            color = (0, 0, 255)
        elif label in GOOD_LABELS:
            color = (0, 255, 0)
        else:
            color = (255, 255, 0)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        display_label = f"{label} (ID:{tid})" if tid is not None else label
        cv2.putText(
            frame,
            display_label,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            2,
        )

        if _DEBUG:
            _draw_debug_overlay(frame, person)

    return frame


def _draw_debug_overlay(frame: np.ndarray, person: dict) -> None:
    overlay = person.get("green_mask_overlay")
    if overlay is not None:
        mask, ox, oy = overlay
        h, w = mask.shape

        # visible rectangle around the lanyard detection region
        cv2.rectangle(frame, (ox, oy), (ox + w, oy + h), (0, 255, 0), 1)

        roi = frame[oy : oy + h, ox : ox + w]
        if roi.shape[:2] == (h, w):
            green_tint = np.full_like(roi, (0, 255, 0), dtype=np.uint8)
            mask_3c = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR) > 0
            alpha = 0.6
            roi[:] = np.where(mask_3c, (roi * (1 - alpha) + green_tint * alpha).astype(np.uint8), roi)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                cnt[:, :, 0] += ox
                cnt[:, :, 1] += oy
                cv2.drawContours(frame, [cnt], -1, (0, 255, 0), 2)

    x1, y1, x2, y2 = person["bbox"]
    x1 = int(x1); y1 = int(y1); x2 = int(x2); y2 = int(y2)

    lines = []
    id_label = person.get("id_label")
    if id_label:
        id_conf = person.get("id_conf", 0)
        lines.append(f"detect={id_label} conf={id_conf:.2f}")

    green_ratio = person.get("green_ratio")
    if green_ratio is not None:
        lines.append(f"green_ratio={green_ratio:.3f}")

    for i, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (x1, y2 + 14 + i * 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )
