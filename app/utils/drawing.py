import cv2
import numpy as np


def draw_people(frame: np.ndarray, people: list[dict]) -> np.ndarray:
    for person in people:
        x1, y1, x2, y2 = person["bbox"]
        tid = person.get("track_id")
        label = person.get("label", "person")

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        display_label = f"{label} (ID:{tid})" if tid is not None else label
        cv2.putText(
            frame,
            display_label,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2,
        )

    return frame
