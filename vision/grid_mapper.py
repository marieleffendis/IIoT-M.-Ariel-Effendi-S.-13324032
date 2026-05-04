from config import GRID_SIZE, WARP_SIZE

CELL_SIZE = WARP_SIZE / GRID_SIZE

def pixel_to_grid(cx, cy):
    col = int(cx // CELL_SIZE)
    row = int(cy // CELL_SIZE)
    return row, col