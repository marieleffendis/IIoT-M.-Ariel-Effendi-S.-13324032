import cv2
import numpy as np
from config import WARP_SIZE

def warp_perspective(frame, pts):
    dst = np.array([
        [0,0],
        [WARP_SIZE,0],
        [WARP_SIZE,WARP_SIZE],
        [0,WARP_SIZE]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(pts, dst)
    warped = cv2.warpPerspective(frame, M, (WARP_SIZE, WARP_SIZE))

    return warped