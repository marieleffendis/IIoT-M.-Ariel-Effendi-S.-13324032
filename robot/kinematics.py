from config import CELL_SIZE_MM, OFFSET_X, OFFSET_Y

def grid_to_world(row, col):
    x = col * CELL_SIZE_MM + OFFSET_X
    y = row * CELL_SIZE_MM + OFFSET_Y
    return x, y