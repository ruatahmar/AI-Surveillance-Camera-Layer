import cv2
from app.detection.video import VideoStream


def main():
    stream = VideoStream(0)
    try:
        while True:
            frame = stream.read()
            if frame is None:
                break

            cv2.imshow("bruhtest", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        stream.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
