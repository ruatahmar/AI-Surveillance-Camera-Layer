import cv2
import numpy as np
from app.detection.video import VideoStream
from app.detection.person import PersonDetector, PersonBox
from app.idCard.detector import IDCardDetector
import sys

MODEL_PATH = "data/models/best.pt"


def parse_source(arg: str) -> str | int:
    if arg.isdigit():
        return int(arg)
    return arg


def main():
    stream: VideoStream = VideoStream()
    # we should prolly have better argument parsing
    if len(sys.argv) == 2:
        stream.open(parse_source(sys.argv[1]))

    detector: PersonDetector = PersonDetector()
    idcard_detector: IDCardDetector = IDCardDetector(model_path=MODEL_PATH, conf=0.1)

    try:
        while True:
            frame: np.ndarray | None = stream.read()  # gets a frame
            if frame is None:
                break

            boxes: list[PersonBox] = detector.detect(
                frame
            )  # detects all people in frame

            for person in boxes:
                x1, y1, x2, y2 = person["bbox"]  # gets cords of person
                _ = cv2.rectangle(
                    frame, (x1, y1), (x2, y2), (0, 255, 0), 2
                )  # makes the rectangle frame

                crop: np.ndarray = frame[
                    y1:y2, x1:x2
                ]  # person cropped out, we should maybe make this crop just the torso part ig
                cv2.imshow("crop", crop)  # for testing/checking purpose
                label: str = idcard_detector.detect(crop)  # labeling the person
                # puts the label on person
                _ = cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 255, 0),
                    2,
                )

            # shows the frame of the vid
            cv2.imshow("bruhtest", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        stream.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
