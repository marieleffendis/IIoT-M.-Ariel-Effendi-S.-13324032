"""
vision/hybrid_detector.py

Detektor hybrid YOLO + HSV.
Deteksi hanya dilakukan di dalam area ROI conveyor.
Koordinat piksel yang dikembalikan adalah koordinat frame penuh (4K),
bukan koordinat relatif ROI.
"""

from ultralytics import YOLO
import cv2
import numpy as np

from vision.perspective import warp_perspective
from config import ROI_X1, ROI_Y1, ROI_X2, ROI_Y2

# ============================================================
# HSV CONFIG
# ============================================================
COLOR_RANGES = {
    "red1"  : ([0,   120, 70],  [10,  255, 255]),
    "red2"  : ([170, 120, 70],  [180, 255, 255]),
    "green" : ([36,  50,  50],  [86,  255, 255]),
    "blue"  : ([100, 50,  50],  [130, 255, 255]),
    "yellow": ([20,  100, 100], [35,  255, 255]),
}

COLORS = ["red", "green", "blue", "yellow"]


# ============================================================
# HSV DETECTOR (validasi warna pada crop)
# ============================================================
def detect_color_hsv(image):
    """
    Tentukan warna dominan pada crop gambar menggunakan analisis HSV.

    Returns:
        str: nama warna ("red"/"green"/"blue"/"yellow") atau None
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    best_color  = None
    max_pixels  = 0

    for color in COLORS:
        if color == "red":
            mask1 = cv2.inRange(hsv, np.array(COLOR_RANGES["red1"][0]),  np.array(COLOR_RANGES["red1"][1]))
            mask2 = cv2.inRange(hsv, np.array(COLOR_RANGES["red2"][0]),  np.array(COLOR_RANGES["red2"][1]))
            mask  = cv2.bitwise_or(mask1, mask2)
        else:
            lower, upper = COLOR_RANGES[color]
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))

        count = cv2.countNonZero(mask)
        if count > max_pixels:
            max_pixels = count
            best_color = color

    return best_color


# ============================================================
# HYBRID DETECTOR
# ============================================================
class HybridDetector:
    def __init__(self, model_path, warp_pts=None):
        self.model    = YOLO(model_path)
        self.warp_pts = warp_pts

    def detect(self, frame):
        """
        Deteksi objek warna pada frame kamera.

        Hanya piksel di dalam ROI (ROI_X1,ROI_Y1)→(ROI_X2,ROI_Y2) yang diproses.
        Koordinat "pixel" di output adalah koordinat frame PENUH (4K), bukan relatif ROI.

        Args:
            frame: frame BGR dari kamera (ukuran penuh, misal 3840×2160)

        Returns:
            list of dict:
                {
                    "color" : str,        # warna final
                    "pixel" : (cx, cy),   # pusat objek di frame penuh
                    "bbox"  : (x1,y1,x2,y2)  # bounding box di frame penuh
                }
        """
        # --- Crop ke ROI ---
        roi = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]

        # --- Opsional: warp perspektif (jika kalibrasi sudah dilakukan) ---
        if self.warp_pts is not None and len(self.warp_pts) == 4:
            roi = warp_perspective(roi, self.warp_pts)

        # --- YOLO inference ---
        results = self.model(roi, conf=0.5)

        objects = []

        for r in results:
            boxes   = r.boxes.xyxy.cpu().numpy()
            classes = r.boxes.cls.cpu().numpy()

            for box, cls in zip(boxes, classes):
                # Koordinat relatif ROI
                x1_roi, y1_roi, x2_roi, y2_roi = map(int, box)

                # Koordinat frame penuh (tambahkan offset ROI)
                x1 = x1_roi + ROI_X1
                y1 = y1_roi + ROI_Y1
                x2 = x2_roi + ROI_X1
                y2 = y2_roi + ROI_Y1

                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                yolo_label = self.model.names[int(cls)]

                # --- HSV Validasi pada crop ROI ---
                crop = roi[y1_roi:y2_roi, x1_roi:x2_roi]
                if crop.size == 0:
                    continue

                hsv_label = detect_color_hsv(crop)

                # --- Keputusan final ---
                final_label = yolo_label
                if hsv_label and hsv_label != yolo_label:
                    print(f"[DETECTOR] Override: YOLO={yolo_label} → HSV={hsv_label}")
                    final_label = hsv_label

                objects.append({
                    "color" : final_label,
                    "pixel" : (cx, cy),
                    "bbox"  : (x1, y1, x2, y2)
                })

        return objects