from ultralytics.models.yolo import YOLO

DATA_PATH = "training/data.yaml"
PROJECT_PATH = "data/models"


def main() -> None:
    model: YOLO = YOLO("yolov8n.pt")

    _ = model.train(
        data=DATA_PATH,
        epochs=50,
        imgsz=640,
        project=PROJECT_PATH,
        name="id_card",
        exist_ok=True,
        device=0,
    )


if __name__ == "__main__":
    main()
