import cv2
from app.detection.video import VideoStream
from app.detection.person import PersonDetector
from app.idCard.detector import IDCardDetector


def main():
    stream = VideoStream(0)
    detector = PersonDetector()
    idcard_dector = IDCardDetector(model_path="data/models/best.pt", conf=0.1)

    try:
        while True:
            frame = stream.read()  # gets a frame
            if frame is None:
                break

            boxes = detector.detect(frame)  # detects all people in frame

            for person in boxes:
                x1, y1, x2, y2 = person["bbox"]  # gets cords of person
                cv2.rectangle(
                    frame, (x1, y1), (x2, y2), (0, 255, 0), 2
                )  # makes the rectangle frame

                crop = frame[
                    y1:y2, x1:x2
                ]  # person cropped out, we should maybe make this crop just the torso part ig
                cv2.imshow("crop", crop)  # for testing/checking purpose
                label = idcard_dector.detect(
                    crop
                )  # labeling the person (example; gavin = racist)
                # puts the label on person
                cv2.putText(
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
