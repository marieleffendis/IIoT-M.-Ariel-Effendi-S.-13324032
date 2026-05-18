from config import (
    DOBOT_ORIGIN_X, DOBOT_ORIGIN_Y,
    DOBOT_Z_PLACE, DOBOT_R,
    CELL_SIZE_MM
)


def grid_to_world(col, row):
    """
    Konversi posisi grid (1-indexed) ke koordinat dunia Dobot.

    Orientasi grid:
        (1,1) = sudut kiri atas papan
        col bertambah → ke kanan  → x Dobot berkurang
        row bertambah → ke bawah  → y Dobot bertambah

    Koordinat referensi aktual (mm):
        (1,1) → (49,  200, -35.0, r=19)
        (2,1) → (29,  200, -35.0, r=19)
        (3,1) → ( 9,  200, -35.0, r=19)
        (4,1) → (-11, 200, -35.0, r=19)  ← formula; konfirmasi fisik diperlukan
        (1,2) → (49,  220, -35.0, r=19)

    Args:
        col (int): kolom 1..4 (kiri ke kanan)
        row (int): baris  1..4 (atas ke bawah)

    Returns:
        (x, y, z, r) dalam mm dan derajat
    """
    x = DOBOT_ORIGIN_X - (col - 1) * CELL_SIZE_MM
    y = DOBOT_ORIGIN_Y + (row - 1) * CELL_SIZE_MM
    z = DOBOT_Z_PLACE
    r = DOBOT_R
    return x, y, z, r