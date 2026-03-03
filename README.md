# AI-Surveillance-Camera-Layer

AI based monitoring using surveillance camera

## workflow

```
Camera
  → grab frame (video.py)
  → run YOLO on full frame → get list of person bounding boxes (person.py)
  → for each person box:
      → crop that region out of the frame
      → run ID card detector on the crop (Person B's job)
      → label that person
  → draw all boxes + labels onto the frame (drawing.py)
  → display the annotated frame
  → repeat
```

This loop runs ~30 times per second (one per frame).

Also everything is called from main.py
