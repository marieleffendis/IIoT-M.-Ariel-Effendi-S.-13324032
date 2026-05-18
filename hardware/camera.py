"""
hardware/camera.py

Kamera Logitech 4K, statis di atas conveyor.
Menyediakan frame capture dan ROI (Region of Interest) untuk deteksi.
"""

import cv2
from config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, ROI_X1, ROI_Y1, ROI_X2, ROI_Y2

# ============================================================
# INISIALISASI KAMERA
# ============================================================
cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

# Cek resolusi aktual (beberapa kamera tidak support 4K penuh)
_actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
_actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"[CAMERA] Resolusi: {_actual_w}×{_actual_h} (target {CAMERA_WIDTH}×{CAMERA_HEIGHT})")


# ============================================================
# API PUBLIK
# ============================================================

def get_frame():
    """Ambil satu frame dari kamera. Return None jika gagal."""
    ret, frame = cap.read()
    if not ret:
        return None
    return frame


def get_roi_crop(frame):
    """
    Kembalikan crop frame sesuai ROI detection zone.
    Koordinat piksel crop mengacu pada konfigurasi ROI_* di config.py.
    """
    return frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]


def draw_roi(frame, color=(0, 255, 255), thickness=3):
    """
    Gambar kotak ROI di atas frame untuk visualisasi (tidak mengubah frame asli).

    Args:
        frame     : frame BGR dari kamera
        color     : warna kotak ROI dalam BGR, default kuning terang
        thickness : ketebalan garis kotak

    Returns:
        frame dengan kotak ROI tergambar
    """
    annotated = frame.copy()

    # Kotak utama ROI
    cv2.rectangle(annotated, (ROI_X1, ROI_Y1), (ROI_X2, ROI_Y2), color, thickness)

    # Label
    label = "DETECTION ZONE"
    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.2
    label_y    = max(ROI_Y1 - 15, 30)
    cv2.putText(annotated, label, (ROI_X1, label_y), font, font_scale, color, 2)

    # Garis tengah vertikal (kalibrasi lebar conveyor ÷ 2)
    mid_x = (ROI_X1 + ROI_X2) // 2
    cv2.line(annotated, (mid_x, ROI_Y1), (mid_x, ROI_Y2), (255, 100, 0), 1)

    return annotated


def release():
    """Lepaskan kamera (panggil saat shutdown)."""
    cap.release()