# AI-Surveillance-Camera-Layer

AI based monitoring using surveillance camera

## workflow

```
Camera
  1. grab frame from video source (video.py)
  2. run YOLO on full frame → get list of person bounding boxes (person.py)
  3. for each person box:
      → crop that region out of the frame
      → run ID card detector on the crop
      → label that person
  4. draw all boxes + labels onto the frame (drawing.py)
  5. display the annotated frame
  6. repeat
```

This loop runs ~30 times per second (one per frame).

Also everything is called from main.py.

currently on step 3;

# immediate needs

- basically do this
- need to find better datasets for id card, so we can actually train yolo to detect them. i think this is most of the work left
- ive tried using [this](https://universe.roboflow.com/ruatas-workspace/id-card-detector-ahb2l-bzw2h/dataset/1), but it had no labels. always check if they have labels first before training, shit takes like 3 hrs
- if you do get a good working dataset that helps detect, but like it still doesnt detect properly maybe change hsv values?

# how shit works

---

maybe we should add a OCR to find usn later
