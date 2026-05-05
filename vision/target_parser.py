import cv2

def detect_color(cell):
    hsv = cv2.cvtColor(cell, cv2.COLOR_BGR2HSV)
    mean = hsv.mean(axis=(0,1))

    h = mean[0]

    if h < 10 or h > 170:
        return "red"
    elif 20 < h < 35:
        return "yellow"
    elif 36 < h < 85:
        return "green"
    elif 90 < h < 130:
        return "blue"

    return None


def parse_target(image):
    grid = {}
    h, w, _ = image.shape

    cell_w = w // 4
    cell_h = h // 4

    for row in range(4):
        for col in range(4):
            cell = image[row*cell_h:(row+1)*cell_h,
                         col*cell_w:(col+1)*cell_w]

            color = detect_color(cell)

            if color:
                grid[color] = (row, col)

    return grid