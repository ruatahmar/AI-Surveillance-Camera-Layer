import cv2
from app.detection.video import VideoStream
from app.detection.person import PersonDetector


def main():
    stream = VideoStream(0)
    detector = PersonDetector()
    try:
        while True:
            frame = stream.read()
            if frame is None:
                break

            boxes = detector.detect(frame)

            # outlines the person in the vid
            for person in boxes:
                x1, y1, x2, y2 = person["bbox"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # shows the frame of the vid
            cv2.imshow("bruhtest", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        stream.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
