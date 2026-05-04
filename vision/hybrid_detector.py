from ultralytics import YOLO
import cv2
import numpy as np

# =========================
# HSV CONFIG
# =========================
COLOR_RANGES = {
    "red1": ([0,120,70], [10,255,255]),
    "red2": ([170,120,70], [180,255,255]),
    "green": ([36,50,50], [86,255,255]),
    "blue": ([100,50,50], [130,255,255]),
    "yellow": ([20,100,100], [35,255,255]),
}

COLORS = ["red", "green", "blue", "yellow"]

# =========================
# HSV DETECTOR (LOCAL)
# =========================
def detect_color_hsv(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    best_color = None
    max_pixels = 0

    for color in COLORS:
        if color == "red":
            mask1 = cv2.inRange(hsv, np.array(COLOR_RANGES["red1"][0]), np.array(COLOR_RANGES["red1"][1]))
            mask2 = cv2.inRange(hsv, np.array(COLOR_RANGES["red2"][0]), np.array(COLOR_RANGES["red2"][1]))
            mask = mask1 | mask2
        else:
            lower, upper = COLOR_RANGES[color]
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))

        count = cv2.countNonZero(mask)

        if count > max_pixels:
            max_pixels = count
            best_color = color

    return best_color


# =========================
# HYBRID DETECTOR
# =========================
class HybridDetector:
    def __init__(self, model_path):
        self.model = YOLO(model_path)

    def detect(self, frame):
        results = self.model(frame, conf=0.5)

        objects = []

        for r in results:
            boxes = r.boxes.xyxy.cpu().numpy()
            classes = r.boxes.cls.cpu().numpy()

            for box, cls in zip(boxes, classes):
                x1, y1, x2, y2 = map(int, box)

                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                yolo_label = self.model.names[int(cls)]

                # =====================
                # HSV VALIDATION
                # =====================
                crop = frame[y1:y2, x1:x2]

                if crop.size == 0:
                    continue

                hsv_label = detect_color_hsv(crop)

                # =====================
                # FINAL DECISION
                # =====================
                final_label = yolo_label

                if hsv_label and hsv_label != yolo_label:
                    print(f"[WARNING] YOLO:{yolo_label} → HSV:{hsv_label}")
                    final_label = hsv_label  # override

                objects.append({
                    "color": final_label,
                    "pixel": (cx, cy),
                    "bbox": (x1, y1, x2, y2)
                })

        return objects