"""
vision/target_parser.py

Parser gambar target 4x4.
Input  : gambar PNG/JPEG yang berisi papan catur 4x4 dengan blok warna.
Output : dict {color: (col, row)} dengan (col, row) 1-indexed.

Alur:
    1. Gambar di-resize ke WARP_SIZE × WARP_SIZE.
    2. Setiap sel (4×4 = 16 sel) dianalisis dominan HSV-nya.
    3. Warna sel dikembalikan bersama posisi grid-nya.

Catatan:
    - Jika dalam satu warna ada lebih dari satu sel, hanya posisi pertama yang disimpan.
      Untuk multi-blok per warna, gunakan parse_target_full().
    - Grid orientasi: (col=1,row=1) = sudut kiri atas.
"""

import cv2
import numpy as np
from config import WARP_SIZE, GRID_SIZE


# ============================================================
# HSV threshold untuk tiap warna
# Threshold dibuat lebih lebar agar toleran terhadap pencahayaan
# ============================================================
_HSV_RANGES = {
    "red"   : [([0,   80, 60],  [15,  255, 255]),
               ([160, 80, 60],  [180, 255, 255])],
    "yellow": [([18,  80, 80],  [38,  255, 255])],
    "green" : [([36,  50, 50],  [90,  255, 255])],
    "blue"  : [([90,  50, 50],  [135, 255, 255])],
}


def _dominant_color(cell_bgr, min_pixel_ratio=0.10):
    """
    Tentukan warna dominan pada crop sel menggunakan HSV masking.

    Args:
        cell_bgr        : crop sel dalam BGR
        min_pixel_ratio : minimal fraksi piksel yang harus cocok agar dianggap warna tsb

    Returns:
        str | None : nama warna, atau None jika tidak ada yang dominan
    """
    if cell_bgr is None or cell_bgr.size == 0:
        return None

    # Sedikit blur untuk kurangi noise
    blurred = cv2.GaussianBlur(cell_bgr, (5, 5), 0)
    hsv     = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    total = cell_bgr.shape[0] * cell_bgr.shape[1]
    best_color  = None
    best_count  = 0

    for color, ranges in _HSV_RANGES.items():
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for (lo, hi) in ranges:
            m = cv2.inRange(hsv, np.array(lo), np.array(hi))
            mask = cv2.bitwise_or(mask, m)

        # Morfologi: hilangkan noise kecil
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        count = cv2.countNonZero(mask)
        if count > best_count:
            best_count = count
            best_color = color

    if best_count / total < min_pixel_ratio:
        return None   # tidak ada warna yang cukup dominan → sel kosong

    return best_color


def parse_target(image):
    """
    Parse gambar target 4x4. Hanya simpan posisi pertama per warna.

    Args:
        image: BGR image (dari cv2.imread atau get_frame)

    Returns:
        dict {color: (col, row)} — 1-indexed, sudut kiri atas = (1,1)

    Contoh return:
        {"red": (1,1), "green": (2,3), "blue": (4,4), "yellow": (3,2)}
    """
    # Resize ke ukuran baku agar sel seragam
    resized   = cv2.resize(image, (WARP_SIZE, WARP_SIZE))
    cell_px   = WARP_SIZE // GRID_SIZE   # ukuran 1 sel dalam piksel

    grid      = {}

    for row in range(1, GRID_SIZE + 1):
        for col in range(1, GRID_SIZE + 1):
            y1 = (row - 1) * cell_px
            y2 =  row      * cell_px
            x1 = (col - 1) * cell_px
            x2 =  col      * cell_px

            cell  = resized[y1:y2, x1:x2]
            color = _dominant_color(cell)

            if color and color not in grid:
                grid[color] = (col, row)

    return grid


def parse_target_full(image):
    """
    Seperti parse_target() tapi mendukung multi-blok per warna.

    Returns:
        dict {color: [(col, row), ...]} — list posisi per warna
    """
    resized   = cv2.resize(image, (WARP_SIZE, WARP_SIZE))
    cell_px   = WARP_SIZE // GRID_SIZE

    grid = {}

    for row in range(1, GRID_SIZE + 1):
        for col in range(1, GRID_SIZE + 1):
            y1 = (row - 1) * cell_px
            y2 =  row      * cell_px
            x1 = (col - 1) * cell_px
            x2 =  col      * cell_px

            cell  = resized[y1:y2, x1:x2]
            color = _dominant_color(cell)

            if color:
                grid.setdefault(color, []).append((col, row))

    return grid