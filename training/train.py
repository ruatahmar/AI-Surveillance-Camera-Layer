from ultralytics import YOLO


def main():
    model = YOLO("yolov8n.pt")

    model.train(
        data="training/data.yaml",
        epochs=50,
        imgsz=640,
        project="data/models",
        name="id_card",
        exist_ok=True,
    )


if __name__ == "__main__":
    main()
