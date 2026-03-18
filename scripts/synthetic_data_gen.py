import cv2
import numpy as np
import random
import os
import argparse
import sys

# Ensure the app directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.detection.pose import PoseDetector


def apply_isometric_warp(img: np.ndarray) -> np.ndarray:
    """
    Applies a perspective transform to simulate a high-angle CCTV view.
    """
    h, w = img.shape[:2]
    has_alpha = img.shape[2] == 4

    src_pts = np.float32([[0, 0], [w, 0], [0, h], [w, h]])

    # Randomly vary the warp for perspective
    tilt_x = random.uniform(0.05, 0.15) * w
    tilt_y = random.uniform(0.02, 0.08) * h
    perspective_squeeze = random.uniform(0.02, 0.05) * w

    dst_pts = np.float32(
        [
            [tilt_x, 0],
            [w - tilt_x, tilt_y],
            [perspective_squeeze, h * 0.95],
            [w - perspective_squeeze, h * 0.98],
        ]
    )

    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(
        img,
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0) if has_alpha else (0, 0, 0),
    )

    mask = warped[:, :, 3] if has_alpha else cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        cnt = max(contours, key=cv2.contourArea)
        x, y, w_c, h_c = cv2.boundingRect(cnt)
        warped = warped[y : y + h_c, x : x + w_c]

    return warped


def overlay_on_background(
    background: np.ndarray, foreground: np.ndarray, x: int, y: int
) -> np.ndarray:
    h_fg, w_fg = foreground.shape[:2]
    h_bg, w_bg = background.shape[:2]

    if x < 0 or y < 0 or x + w_fg > w_bg or y + h_fg > h_bg:
        return background

    if foreground.shape[2] != 4:
        background[y : y + h_fg, x : x + w_fg] = foreground
        return background

    alpha_fg = foreground[:, :, 3] / 255.0
    alpha_bg = 1.0 - alpha_fg

    for c in range(0, 3):
        background[y : y + h_fg, x : x + w_fg, c] = (
            alpha_fg * foreground[:, :, c]
            + alpha_bg * background[y : y + h_fg, x : x + w_fg, c]
        )

    return background


def generate_dataset(
    bg_dir: str,
    student_template: str,
    teacher_template: str = None,
    output_dir: str = "training/dataset_v2",
):
    os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "labels"), exist_ok=True)

    # Now using PoseDetector for better placement and scale
    detector = PoseDetector()

    s_temp = cv2.imread(student_template, cv2.IMREAD_UNCHANGED)
    t_temp = (
        cv2.imread(teacher_template, cv2.IMREAD_UNCHANGED)
        if teacher_template
        else None
    )

    if s_temp is None:
        print(f"Error: Could not load student template from {student_template}")
        return

    bg_files = [
        f for f in os.listdir(bg_dir) if f.lower().endswith((".jpg", ".png", ".jpeg"))
    ]
    print(f"Found {len(bg_files)} background images. Generating dataset...")

    for bg_file in bg_files:
        bg_path = os.path.join(bg_dir, bg_file)
        bg_img = cv2.imread(bg_path)
        if bg_img is None:
            continue

        h_bg, w_bg = bg_img.shape[:2]
        detections = detector.detect(bg_img)

        yolo_labels = []

        for person in detections:
            kp = person["keypoints"]
            
            # 1. Orientation Check: 
            # If we can't see BOTH shoulders, skip (likely facing away or side)
            if not kp["left_shoulder"] or not kp["right_shoulder"]:
                continue
            
            # 2. Scale Calculation:
            # Use shoulder-to-shoulder width to scale the ID card (roughly 35% of shoulder width)
            l_sh = np.array(kp["left_shoulder"])
            r_sh = np.array(kp["right_shoulder"])
            shoulder_width = np.linalg.norm(l_sh - r_sh)
            
            # 3. Placement (Sternum/Chest):
            # Find the midpoint between shoulders and drop down slightly
            midpoint = (l_sh + r_sh) / 2
            sternum_y = int(midpoint[1] + (shoulder_width * 0.2))
            sternum_x = int(midpoint[0])

            # Class selection
            if t_temp is not None:
                is_teacher = random.random() > 0.5
                class_id = 1 if is_teacher else 0
                template = t_temp if is_teacher else s_temp
            else:
                class_id = 0
                template = s_temp

            # Resize based on shoulder width (Scale issue: FIXED)
            target_w = int(shoulder_width * 0.35)
            if target_w < 5:  # Skip if the ID would be too small to be useful
                continue
                
            aspect_ratio = template.shape[0] / template.shape[1]
            target_h = int(target_w * aspect_ratio)
            
            # Final safety check for dimensions
            if target_w < 1 or target_h < 1:
                continue

            resized_temp = cv2.resize(template, (target_w, target_h))

            # Apply warp (Removed CCTV effects: FIXED)
            warped = apply_isometric_warp(resized_temp)

            # Center the warped image on the sternum
            paste_x = sternum_x - (warped.shape[1] // 2)
            paste_y = sternum_y - (warped.shape[0] // 2)

            # Overlay
            bg_img = overlay_on_background(bg_img, warped, paste_x, paste_y)

            # Labeling
            id_w, id_h = warped.shape[1], warped.shape[0]
            xc, yc = (paste_x + id_w / 2) / w_bg, (paste_y + id_h / 2) / h_bg
            wn, hn = id_w / w_bg, id_h / h_bg
            yolo_labels.append(f"{class_id} {xc:.6f} {yc:.6f} {wn:.6f} {hn:.6f}")

        # Save
        if yolo_labels:
            base_name = os.path.splitext(bg_file)[0]
            cv2.imwrite(
                os.path.join(output_dir, "images", f"{base_name}_syn.jpg"), bg_img
            )
            with open(
                os.path.join(output_dir, "labels", f"{base_name}_syn.txt"), "w"
            ) as f:
                f.write("\n".join(yolo_labels))

    print(f"Dataset generation complete in {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pose-Aware Synthetic ID Dataset Generator"
    )
    parser.add_argument(
        "--backgrounds", required=True, help="Folder containing background images"
    )
    parser.add_argument("--student", required=True, help="Transparent PNG of Student ID")
    parser.add_argument("--teacher", help="Optional: Transparent PNG of Teacher ID")
    parser.add_argument(
        "--output", default="training/dataset_v2", help="Where to save the dataset"
    )

    args = parser.parse_args()
    generate_dataset(args.backgrounds, args.student, args.teacher, args.output)
